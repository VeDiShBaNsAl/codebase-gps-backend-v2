import logging
from app.models.graph import GraphNode, GraphEdge
logger = logging.getLogger("codebase_gps")

def analyze_repository(repository_path: str) -> dict:
    try:
        from code_intelligence import analyze_repository as real_analyze
        return real_analyze(repository_path)
    except ImportError as exc:
        # This should only happen in deployments where the optional package was
        # deliberately omitted; do not conceal analyzer defects as demo data.
        logger.warning("code_intelligence module not found (%s). Using STUB analyzer.", exc)
        return {
            "nodes": [
                GraphNode(id="file_main", type="FILE", name="main.py", file_path="main.py", start_line=1, end_line=50, language="python"),
                GraphNode(id="func_app", type="FUNCTION", name="create_app", file_path="main.py", start_line=10, end_line=25, language="python")
            ],
            "edges": [
                GraphEdge(source="file_main", target="func_app", type="CONTAINS", resolution="resolved", source_file="main.py", source_line=10)
            ],
            "languages": ["python"],
            "total_files": 1,
            "total_symbols": 1,
            "total_relationships": 1
        }
