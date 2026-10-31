import json, logging
from app.database.db import get_db_connection
from app.services.ingestion_service import clone_repository
from app.services.analysis_service import analyze_repository
logger = logging.getLogger("codebase_gps")

def run_indexing_pipeline(repo_id: str, repo_url: str, branch: str):
    def update_stage(stage: str, progress: int, status: str = "processing", error: str = None):
        with get_db_connection() as conn:
            conn.execute("UPDATE repositories SET status = ?, current_stage = ?, progress = ?, error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, stage, progress, error, repo_id))
    try:
        update_stage("cloning", 10)
        local_path = clone_repository(repo_url, branch, repo_id)
        with get_db_connection() as conn:
            conn.execute("UPDATE repositories SET local_path = ? WHERE id = ?", (local_path, repo_id))
        update_stage("detecting_languages", 25)
        update_stage("parsing", 40)
        res = analyze_repository(local_path)
        update_stage("building_graph", 70)
        update_stage("indexing_search", 90)
        with get_db_connection() as conn:
            for node in res.get("nodes", []):
                conn.execute("INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (node.id, repo_id, node.type, node.name, node.file_path, node.start_line, node.end_line, node.language))
            for edge in res.get("edges", []):
                conn.execute("INSERT INTO edges(repo_id, source, target, type, resolution, source_file, source_line) VALUES (?, ?, ?, ?, ?, ?, ?)", (repo_id, edge.source, edge.target, edge.type, edge.resolution, edge.source_file, edge.source_line))
            for node in res.get("nodes", []):
                conn.execute("INSERT INTO symbols_fts VALUES (?, ?, ?, ?, ?)", (repo_id, node.id, node.name, node.file_path, f"{node.type} {node.name}"))
            conn.execute("UPDATE repositories SET total_files = ?, total_symbols = ?, total_relationships = ?, languages = ? WHERE id = ?", (res.get("total_files", 0), res.get("total_symbols", 0), res.get("total_relationships", 0), json.dumps(res.get("languages", [])), repo_id))
        update_stage("completed", 100, status="completed")
    except Exception as exc:
        logger.exception("Indexing failed: %s", exc)
        update_stage("failed", 0, status="failed", error=str(exc))
