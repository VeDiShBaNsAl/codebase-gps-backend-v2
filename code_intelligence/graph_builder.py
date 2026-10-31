"""Repository-level graph assembly and traversal helpers."""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

from app.models.graph import GraphEdge, GraphNode
from .analyzer import analyze_file
from .analyzer import stable_id
from .file_discovery import discover_source_files
from .models import PendingEdge


def _resolve_target(edge: PendingEdge, nodes: list[GraphNode]) -> tuple[str | None, str]:
    """Resolve names conservatively; ambiguous names remain explicitly unresolved."""
    reference = edge.target_name.lstrip(".").lstrip("/")
    basename = reference.rsplit(".", 1)[-1]
    named = [node for node in nodes if node.name == basename]
    if edge.type == "IMPORTS":
        module_path = reference.replace(".", "/")
        matches = [node for node in nodes if node.type == "FILE" and (node.file_path.rsplit(".", 1)[0] == module_path or node.file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0] == basename)]
        named = matches or named
    local = [node for node in named if node.file_path == edge.source_file]
    candidates = local or named
    if len(candidates) == 1:
        return candidates[0].id, "resolved"
    return None, "unresolved"


def _serialize(nodes: list[GraphNode], edges: list[GraphEdge], paths: list[Path]) -> dict:
    languages = sorted({node.language for node in nodes if node.type == "FILE"})
    return {"nodes": nodes, "edges": edges, "languages": languages, "total_files": len(paths), "total_symbols": sum(node.type not in {"FILE", "DIRECTORY", "REPOSITORY"} for node in nodes), "total_relationships": len(edges)}


def analyze_repository(repo_path: str) -> dict:
    """Return a JSON-compatible typed graph for a local repository path."""
    root = Path(repo_path).resolve()
    paths = discover_source_files(str(root))
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    pending: list[PendingEdge] = []
    for path in paths:
        parsed = analyze_file(root, path)
        nodes.extend(parsed.nodes); edges.extend(parsed.edges); pending.extend(parsed.pending_edges)
    for edge in pending:
        target, resolution = _resolve_target(edge, nodes)
        # Retain unresolved evidence instead of inventing a relationship.  The
        # target deliberately has no node: consumers can show it as unresolved
        # and the intelligence adapter reports it as a diagnostic.
        target = target or stable_id("UNRESOLVED", edge.source_file, edge.target_name, edge.source_line)
        edges.append(GraphEdge(source=edge.source, target=target, type=edge.type, resolution=resolution, source_file=edge.source_file, source_line=edge.source_line))
    # Keep response stable and avoid duplicated relationships from repeated calls.
    unique = {(edge.source, edge.target, edge.type, edge.source_file, edge.source_line): edge for edge in edges}
    ordered_nodes = sorted(nodes, key=lambda node: node.id)
    ordered_edges = sorted(unique.values(), key=lambda edge: (edge.source, edge.target, edge.type, edge.source_line))
    return _serialize(ordered_nodes, ordered_edges, paths)


def _walk(graph: dict, symbol_id: str, depth: int, reverse: bool) -> list[str]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in graph.get("edges", []):
        if edge.type not in {"CALLS", "DEPENDS_ON", "REFERENCES"} or edge.resolution != "resolved":
            continue
        origin, target = (edge.target, edge.source) if reverse else (edge.source, edge.target)
        adjacency[origin].append(target)
    queue, seen, result = deque([(symbol_id, 0)]), {symbol_id}, []
    while queue:
        current, distance = queue.popleft()
        if distance >= depth:
            continue
        for target in sorted(adjacency[current]):
            if target not in seen:
                seen.add(target); result.append(target); queue.append((target, distance + 1))
    return result


def direct_callers(graph: dict, symbol_id: str, depth: int = 1) -> list[str]:
    return _walk(graph, symbol_id, depth, reverse=True)


def dependencies(graph: dict, symbol_id: str, depth: int = 1) -> list[str]:
    return _walk(graph, symbol_id, depth, reverse=False)
