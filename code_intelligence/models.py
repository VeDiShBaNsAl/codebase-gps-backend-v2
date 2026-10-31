"""Shared graph types and small intermediate representations."""
from __future__ import annotations

from dataclasses import dataclass

from app.models.graph import GraphEdge as Edge
from app.models.graph import GraphNode as Node


@dataclass(frozen=True)
class PendingEdge:
    """An edge whose target is resolved only after every file is parsed."""

    source: str
    target_name: str
    type: str
    source_file: str
    source_line: int
    target_file: str | None = None


@dataclass
class FileAnalysis:
    nodes: list[Node]
    edges: list[Edge]
    pending_edges: list[PendingEdge]
