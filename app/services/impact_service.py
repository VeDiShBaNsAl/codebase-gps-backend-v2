def analyze_impact(repo_id: str, symbol_id: str, depth: int, local_path: str) -> dict:
    return {"target": {"name": symbol_id, "file_path": "main.py"}, "direct_callers": [], "dependent_modules": [], "related_tests": [], "unresolved_relationships": [], "limitations": ["Stub report"]}
