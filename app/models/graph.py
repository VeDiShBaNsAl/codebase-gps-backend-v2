from typing import Literal
from pydantic import BaseModel

NodeType = Literal["REPOSITORY", "DIRECTORY", "FILE", "CLASS", "FUNCTION", "METHOD", "TEST"]
EdgeType = Literal["CONTAINS", "IMPORTS", "CALLS", "DEFINES", "EXTENDS", "REFERENCES", "TESTS", "DEPENDS_ON"]
EdgeResolution = Literal["resolved", "unresolved", "inferred"]

class GraphNode(BaseModel):
    id: str
    type: NodeType
    name: str
    file_path: str
    start_line: int
    end_line: int
    language: str

class GraphEdge(BaseModel):
    source: str
    target: str
    type: EdgeType
    resolution: EdgeResolution
    source_file: str
    source_line: int

class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
