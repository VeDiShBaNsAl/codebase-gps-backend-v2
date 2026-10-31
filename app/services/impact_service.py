"""Existing impact API contract backed by the Person 4 impact engine."""
from fastapi import HTTPException

from app.services.intelligence_adapter import impact_repository


def analyze_impact(repo_id: str, symbol_id: str, depth: int, local_path: str = "") -> dict:
    report = impact_repository(repo_id, symbol_id, depth)
    if report is None:
        raise HTTPException(status_code=404, detail="Symbol not found.")
    return {"target": report["selected_component"], "direct_callers": [item for item in report["dependents"] if not item["component"]["is_test"]], "dependent_modules": [], "related_tests": report["related_tests"], "unresolved_relationships": [], "limitations": [], "dependencies": report["dependencies"], "diagnostics": report["diagnostics"]}
