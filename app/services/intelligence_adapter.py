"""Adapter between Person 1 SQLite graph records and Person 4 intelligence input."""
from __future__ import annotations

from app.database.db import get_db_connection
from app.intelligence.engine import impact, investigate

TYPE_MAP = {"FUNCTION": "function", "METHOD": "method", "CLASS": "class", "TEST": "test", "FILE": "file", "DIRECTORY": "directory"}
DEPENDENCY_TYPES = {"CALLS", "DEPENDS_ON"}


def load_snapshot(repo_id: str) -> dict:
    with get_db_connection() as conn:
        nodes = conn.execute("SELECT id, type, name, file_path, start_line, end_line FROM nodes WHERE repo_id = ?", (repo_id,)).fetchall()
        edges = conn.execute("SELECT source, target, type, resolution, source_file, source_line FROM edges WHERE repo_id = ?", (repo_id,)).fetchall()
    components = []
    for node in nodes:
        kind = TYPE_MAP.get(node["type"])
        if kind:
            components.append({"id": node["id"], "name": node["name"], "kind": kind, "location": {"path": node["file_path"], "start_line": node["start_line"], "end_line": node["end_line"]}, "content": "", "is_test": kind == "test"})
    known = {component["id"] for component in components}; dependencies, test_edges, diagnostics = [], [], []
    for edge in edges:
        if edge["source"] not in known or edge["target"] not in known:
            diagnostics.append(f"Ignored graph edge {edge['source']} -> {edge['target']}: unknown normalized component endpoint.")
            continue
        normalized = {"source_id": edge["source"], "target_id": edge["target"], "location": {"path": edge["source_file"], "start_line": edge["source_line"], "end_line": edge["source_line"]}, "evidence": f"{edge['type']} edge ({edge['resolution']})"}
        if edge["type"] in DEPENDENCY_TYPES or (edge["type"] == "REFERENCES" and edge["resolution"] == "resolved"):
            dependencies.append(normalized)
        elif edge["type"] == "TESTS":
            test_edges.append(normalized)
    return {"components": components, "dependency_edges": dependencies, "test_edges": test_edges, "diagnostics": diagnostics}


def investigate_repository(repo_id: str, issue: dict, max_results: int = 10, depth: int = 2) -> dict:
    return investigate(issue, load_snapshot(repo_id), max_results, depth)


def impact_repository(repo_id: str, symbol_id: str, depth: int = 1) -> dict | None:
    return impact(symbol_id, load_snapshot(repo_id), depth)
