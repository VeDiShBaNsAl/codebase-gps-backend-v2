import uuid, json, os
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from app.models.schemas import IndexRequest, IndexResponse, StatusResponse, RepoDetailResponse, SearchResponse, SearchResultItem, SymbolDetailResponse, IssueAnalyzeRequest, IssueInvestigationReport, ImpactRequest, ImpactReport
from app.models.graph import GraphResponse, GraphNode, GraphEdge
from app.services.repo_validation import validate_repo_url, validate_branch
from app.services.github_client import GitHubClient
from app.services.indexing_service import run_indexing_pipeline
from app.services.issue_service import analyze_issue
from app.services.impact_service import analyze_impact
from app.database.db import get_db_connection

router = APIRouter(prefix="/api/repos", tags=["repositories"])

@router.post("/index", response_model=IndexResponse, status_code=202)
async def index_repository(payload: IndexRequest, background_tasks: BackgroundTasks):
    owner, repo, normalized_url = validate_repo_url(payload.repo_url)
    clean_branch = validate_branch(payload.branch)
    github = GitHubClient()
    await github.get_repo_metadata(owner, repo)
    repo_id = str(uuid.uuid4())[:8]
    with get_db_connection() as conn:
        conn.execute("INSERT INTO repositories (id, owner, name, url, branch, status, current_stage, progress) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (repo_id, owner, repo, normalized_url, clean_branch, "queued", "queued", 0))
    background_tasks.add_task(run_indexing_pipeline, repo_id, normalized_url, clean_branch)
    return IndexResponse(repo_id=repo_id, status="queued")

@router.get("/{repo_id}/status", response_model=StatusResponse)
def get_repo_status(repo_id: str):
    with get_db_connection() as conn:
        row = conn.execute("SELECT id, status, progress, current_stage, error FROM repositories WHERE id = ?", (repo_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Repository not found.")
        return StatusResponse(repo_id=row["id"], status=row["status"], progress=row["progress"], current_stage=row["current_stage"], error=row["error"])

@router.get("/{repo_id}", response_model=RepoDetailResponse)
def get_repo_detail(repo_id: str):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Repository not found.")
        return RepoDetailResponse(repo_id=row["id"], owner=row["owner"], name=row["name"], url=row["url"], branch=row["branch"], supported_languages=json.loads(row["languages"]), total_files=row["total_files"], total_symbols=row["total_symbols"], total_relationships=row["total_relationships"], indexing_status=row["status"])

@router.get("/{repo_id}/graph", response_model=GraphResponse)
def get_repo_graph(repo_id: str):
    with get_db_connection() as conn:
        if not conn.execute("SELECT id FROM repositories WHERE id = ?", (repo_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Repository not found.")
        nodes = [GraphNode(id=r["id"], type=r["type"], name=r["name"], file_path=r["file_path"], start_line=r["start_line"], end_line=r["end_line"], language=r["language"]) for r in conn.execute("SELECT * FROM nodes WHERE repo_id = ?", (repo_id,)).fetchall()]
        edges = [GraphEdge(source=r["source"], target=r["target"], type=r["type"], resolution=r["resolution"], source_file=r["source_file"], source_line=r["source_line"]) for r in conn.execute("SELECT * FROM edges WHERE repo_id = ?", (repo_id,)).fetchall()]
        return GraphResponse(nodes=nodes, edges=edges)

@router.get("/{repo_id}/search", response_model=SearchResponse)
def search_repository(repo_id: str, q: str = Query(..., min_length=1)):
    with get_db_connection() as conn:
        if not conn.execute("SELECT id FROM repositories WHERE id = ?", (repo_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Repository not found.")
        rows = conn.execute("SELECT symbol_id, name, file_path, docstring FROM symbols_fts WHERE repo_id = ? AND symbols_fts MATCH ? LIMIT 20", (repo_id, q)).fetchall()
        return SearchResponse(results=[SearchResultItem(id=r["symbol_id"], type="SYMBOL", name=r["name"], file_path=r["file_path"], snippet=r["docstring"] or "") for r in rows])

@router.get("/{repo_id}/symbols/{symbol_id}", response_model=SymbolDetailResponse)
def get_symbol_detail(repo_id: str, symbol_id: str):
    with get_db_connection() as conn:
        repo = conn.execute("SELECT local_path FROM repositories WHERE id = ?", (repo_id,)).fetchone()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
        node = conn.execute("SELECT * FROM nodes WHERE repo_id = ? AND id = ?", (repo_id, symbol_id)).fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="Symbol not found.")
        return SymbolDetailResponse(symbol_id=symbol_id, metadata=dict(node), source_code_lines=[], file_location=node["file_path"], relationships=[], related_tests=[])

@router.post("/{repo_id}/issues/analyze", response_model=IssueInvestigationReport)
async def analyze_repo_issue(repo_id: str, payload: IssueAnalyzeRequest):
    with get_db_connection() as conn:
        repo = conn.execute("SELECT local_path FROM repositories WHERE id = ?", (repo_id,)).fetchone()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
        return await analyze_issue(repo_id, payload)

@router.post("/{repo_id}/impact", response_model=ImpactReport)
async def analyze_repo_impact(repo_id: str, payload: ImpactRequest):
    with get_db_connection() as conn:
        repo = conn.execute("SELECT local_path FROM repositories WHERE id = ?", (repo_id,)).fetchone()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
        return analyze_impact(repo_id, payload.symbol_id, payload.depth, repo["local_path"] or "")
