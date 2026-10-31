from app.config.settings import settings
from app.database.db import get_db_connection, init_db
from app.main import app
from app.models.schemas import IssueAnalyzeRequest
from app.services.intelligence_adapter import impact_repository, investigate_repository, load_snapshot
from fastapi.testclient import TestClient


def populate_sqlite_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(settings, "database_url", str(tmp_path / "integration.db"))
    init_db()
    with get_db_connection() as conn:
        conn.execute("INSERT INTO repositories (id, owner, name, url, branch, status, current_stage, progress) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ("repo1", "owner", "repo", "https://github.com/owner/repo", "main", "completed", "completed", 100))
        nodes = [
            ("reset", "FUNCTION", "resetPassword", "src/api.py", 10, 20, "python"),
            ("revoke", "FUNCTION", "revoke_sessions", "src/auth.py", 30, 40, "python"),
            ("store", "METHOD", "delete_sessions", "src/store.py", 5, 10, "python"),
            ("test_reset", "TEST", "test_reset_revokes", "tests/test_auth.py", 8, 15, "python"),
            ("auth_file", "FILE", "src/auth.py", "src/auth.py", 1, 50, "python"),
            ("auth_dir", "DIRECTORY", "src/auth", "src/auth", 1, 1, "python"),
        ]
        for node in nodes:
            conn.execute("INSERT INTO nodes (id, repo_id, type, name, file_path, start_line, end_line, language) VALUES (?, 'repo1', ?, ?, ?, ?, ?, ?)", node)
        edges = [
            ("reset", "revoke", "CALLS", "resolved", "src/api.py", 17),
            ("revoke", "store", "DEPENDS_ON", "resolved", "src/auth.py", 36),
            ("reset", "store", "REFERENCES", "resolved", "src/api.py", 18),
            ("store", "reset", "REFERENCES", "inferred", "src/store.py", 9),
            ("auth_file", "revoke", "CONTAINS", "resolved", "src/auth.py", 1),
            ("auth_file", "reset", "DEFINES", "resolved", "src/auth.py", 1),
            ("test_reset", "reset", "TESTS", "resolved", "tests/test_auth.py", 12),
        ]
        for edge in edges:
            conn.execute("INSERT INTO edges (repo_id, source, target, type, resolution, source_file, source_line) VALUES ('repo1', ?, ?, ?, ?, ?, ?)", edge)


def test_sqlite_adapter_normalizes_nodes_filters_edges_and_discovers_tests(tmp_path, monkeypatch):
    populate_sqlite_fixture(tmp_path, monkeypatch)

    snapshot = load_snapshot("repo1")
    assert {component["id"] for component in snapshot["components"]} == {"reset", "revoke", "store", "test_reset", "auth_file", "auth_dir"}
    assert {edge["source_id"] + "->" + edge["target_id"] for edge in snapshot["dependency_edges"]} == {"reset->revoke", "revoke->store", "reset->store"}
    assert [(edge["source_id"], edge["target_id"]) for edge in snapshot["test_edges"]] == [("test_reset", "reset")]
    assert snapshot["dependency_edges"][0]["location"] == {"path": "src/api.py", "start_line": 17, "end_line": 17}

    investigation = investigate_repository("repo1", {"title": "Password reset revokes sessions", "description": ""})
    assert all(not item["component"]["is_test"] for item in investigation["ranked_components"])
    assert [item["component"]["id"] for item in investigation["related_tests"]] == ["test_reset"]

    report = impact_repository("repo1", "revoke", depth=3)
    assert {item["component"]["id"] for item in report["dependencies"]} == {"store"}
    assert {item["component"]["id"] for item in report["dependents"]} == {"reset"}


def test_issue_request_preserves_url_contract_and_supports_direct_issue_text():
    assert IssueAnalyzeRequest(issue_url="https://github.com/owner/repo/issues/7").issue_url
    assert IssueAnalyzeRequest(title="Fix session revocation", description="body").title == "Fix session revocation"


def test_existing_routes_use_sqlite_snapshot_for_investigation_and_impact(tmp_path, monkeypatch):
    populate_sqlite_fixture(tmp_path, monkeypatch)
    with TestClient(app) as client:
        investigation = client.post("/api/repos/repo1/issues/analyze", json={"title": "Password reset revokes sessions"})
        impact = client.post("/api/repos/repo1/impact", json={"symbol_id": "revoke", "depth": 3})

    assert investigation.status_code == 200
    assert investigation.json()["related_tests"][0]["component"]["id"] == "test_reset"
    assert impact.status_code == 200
    assert impact.json()["dependencies"][0]["component"]["id"] == "store"
