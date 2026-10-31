"""Language adapters that extract static structure without executing source code."""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from app.models.graph import GraphEdge, GraphNode
from .models import FileAnalysis, PendingEdge


def stable_id(kind: str, path: str, name: str, line: int) -> str:
    digest = hashlib.sha1(f"{kind}:{path}:{name}:{line}".encode()).hexdigest()[:12]
    return f"{kind.lower()}:{digest}"


def _end_line(node: ast.AST) -> int:
    return int(getattr(node, "end_lineno", getattr(node, "lineno", 1)))


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = [node.attr]
        value = node.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return None


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, path: str, language: str, file_id: str) -> None:
        self.path, self.language, self.file_id = path, language, file_id
        self.nodes: list[GraphNode] = []
        self.edges: list[GraphEdge] = []
        self.pending: list[PendingEdge] = []
        self.scope: list[tuple[str, str]] = []  # (id, class-or-function marker)

    def _add_symbol(self, node: ast.AST, name: str, kind: str) -> str:
        line = int(getattr(node, "lineno", 1))
        node_id = stable_id(kind, self.path, name, line)
        is_test = name.startswith("test_") or "/tests/" in f"/{self.path}" or self.path.startswith("tests/")
        if is_test and kind in {"FUNCTION", "METHOD"}:
            kind = "TEST"
        self.nodes.append(GraphNode(id=node_id, type=kind, name=name, file_path=self.path, start_line=line, end_line=_end_line(node), language=self.language))
        parent_id = self.scope[-1][0] if self.scope else self.file_id
        self.edges.append(GraphEdge(source=parent_id, target=node_id, type="CONTAINS", resolution="resolved", source_file=self.path, source_line=line))
        return node_id

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        node_id = self._add_symbol(node, node.name, "CLASS")
        for base in node.bases:
            name = _call_name(base)
            if name:
                self.pending.append(PendingEdge(node_id, name, "EXTENDS", self.path, int(getattr(base, "lineno", node.lineno))))
        self.scope.append((node_id, "class")); self.generic_visit(node); self.scope.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        kind = "METHOD" if self.scope and self.scope[-1][1] == "class" else "FUNCTION"
        node_id = self._add_symbol(node, node.name, kind)
        self.scope.append((node_id, "function")); self.generic_visit(node); self.scope.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Import(self, node: ast.Import) -> None:
        source = self.scope[-1][0] if self.scope else self.file_id
        for alias in node.names:
            self.pending.append(PendingEdge(source, alias.name, "IMPORTS", self.path, node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        source = self.scope[-1][0] if self.scope else self.file_id
        module = ("." * node.level) + (node.module or "")
        self.pending.append(PendingEdge(source, module, "IMPORTS", self.path, node.lineno))

    def visit_Call(self, node: ast.Call) -> None:
        if self.scope:
            name = _call_name(node.func)
            if name:
                self.pending.append(PendingEdge(self.scope[-1][0], name, "CALLS", self.path, node.lineno))
        self.generic_visit(node)


_JS_IMPORT = re.compile(r"^\s*import(?:[\s\S]*?from\s*)?[\"']([^\"']+)[\"']|^\s*require\(\s*[\"']([^\"']+)[\"']\s*\)", re.MULTILINE)
_JS_FUNCTION = re.compile(r"(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(|(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", re.MULTILINE)
_JS_CLASS = re.compile(r"(?:^|\n)\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+([A-Za-z_$][\w$.]*))?", re.MULTILINE)
_JS_CALL = re.compile(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\s*\(")


def _line_at(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def _analyze_javascript(source: str, path: str, language: str, file_id: str) -> FileAnalysis:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    pending: list[PendingEdge] = []
    symbols: list[tuple[str, str, int, int]] = []
    for match in _JS_CLASS.finditer(source):
        name, parent = match.group(1), match.group(2)
        line = _line_at(source, match.start())
        node_id = stable_id("CLASS", path, name, line)
        nodes.append(GraphNode(id=node_id, type="CLASS", name=name, file_path=path, start_line=line, end_line=line, language=language))
        edges.append(GraphEdge(source=file_id, target=node_id, type="CONTAINS", resolution="resolved", source_file=path, source_line=line))
        symbols.append((node_id, name, line, match.start()))
        if parent:
            pending.append(PendingEdge(node_id, parent, "EXTENDS", path, line))
    for match in _JS_FUNCTION.finditer(source):
        name = match.group(1) or match.group(2)
        line = _line_at(source, match.start())
        kind = "TEST" if name.startswith("test") or "/tests/" in f"/{path}" else "FUNCTION"
        node_id = stable_id(kind, path, name, line)
        nodes.append(GraphNode(id=node_id, type=kind, name=name, file_path=path, start_line=line, end_line=line, language=language))
        edges.append(GraphEdge(source=file_id, target=node_id, type="CONTAINS", resolution="resolved", source_file=path, source_line=line))
        symbols.append((node_id, name, line, match.start()))
    for match in _JS_IMPORT.finditer(source):
        pending.append(PendingEdge(file_id, match.group(1) or match.group(2), "IMPORTS", path, _line_at(source, match.start())))
    for index, (node_id, _, start_line, offset) in enumerate(symbols):
        # The lightweight adapter does not try to parse nested braces, but it
        # must at least stop at the next top-level declaration.
        next_symbol_offset = symbols[index + 1][3] if index + 1 < len(symbols) else len(source)
        closing_brace = source.find("\n}", offset, next_symbol_offset)
        end_offset = closing_brace if closing_brace >= 0 else next_symbol_offset
        body = source[offset:end_offset]
        for call in _JS_CALL.finditer(body):
            name = call.group(1)
            if name not in {"if", "for", "while", "switch", "catch", "function"}:
                pending.append(PendingEdge(node_id, name, "CALLS", path, start_line + body.count("\n", 0, call.start())))
    return FileAnalysis(nodes, edges, pending)


def analyze_file(root: Path, path: Path) -> FileAnalysis:
    """Analyze one source file; syntax errors simply yield its file node."""
    relative = path.relative_to(root).as_posix()
    language = "python" if path.suffix.lower() == ".py" else ("typescript" if path.suffix.lower() in {".ts", ".tsx"} else "javascript")
    source = path.read_text(encoding="utf-8", errors="replace")
    file_id = stable_id("FILE", relative, path.name, 1)
    result = FileAnalysis([GraphNode(id=file_id, type="FILE", name=path.name, file_path=relative, start_line=1, end_line=max(1, source.count("\n") + 1), language=language)], [], [])
    if language != "python":
        parsed = _analyze_javascript(source, relative, language, file_id)
        return FileAnalysis(result.nodes + parsed.nodes, result.edges + parsed.edges, parsed.pending_edges)
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError:
        return result
    visitor = _PythonVisitor(relative, language, file_id)
    visitor.visit(tree)
    return FileAnalysis(result.nodes + visitor.nodes, result.edges + visitor.edges, visitor.pending)
