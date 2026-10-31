from typing import Any, Literal
from pydantic import BaseModel, Field

IndexStatus = Literal["queued", "processing", "completed", "failed"]

class IndexRequest(BaseModel):
    repo_url: str
    branch: str = "main"

class IndexResponse(BaseModel):
    repo_id: str
    status: IndexStatus

class StatusResponse(BaseModel):
    repo_id: str
    status: IndexStatus
    progress: int
    current_stage: str

class RepoDetailResponse(BaseModel):
    repo_id: str
    owner: str
    name: str
    url: str
    branch: str
    supported_languages: list[str]
    total_files: int
    total_symbols: int
    total_relationships: int
    indexing_status: IndexStatus

class SearchResultItem(BaseModel):
    id: str
    type: str
    name: str
    file_path: str
    snippet: str

class SearchResponse(BaseModel):
    results: list[SearchResultItem]

class SymbolDetailResponse(BaseModel):
    symbol_id: str
    metadata: dict[str, Any]
    source_code_lines: list[str]
    file_location: str
    relationships: list[dict[str, Any]]
    related_tests: list[dict[str, Any]]

class IssueAnalyzeRequest(BaseModel):
    issue_url: str

class IssueInvestigationReport(BaseModel):
    issue: dict[str, Any]
    results: list[dict[str, Any]]
    limitations: list[str] = []

class ImpactRequest(BaseModel):
    symbol_id: str
    depth: int = Field(default=1, ge=1, le=5)

class ImpactReport(BaseModel):
    target: dict[str, Any]
    direct_callers: list[dict[str, Any]] = []
    dependent_modules: list[dict[str, Any]] = []
    related_tests: list[dict[str, Any]] = []
    unresolved_relationships: list[dict[str, Any]] = []
    limitations: list[str] = []
