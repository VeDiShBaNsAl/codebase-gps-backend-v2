from fastapi.testclient import TestClient
from app.main import app
from app.config.settings import settings
from app.database.db import get_db_connection, init_db
client = TestClient(app)
def test_health():
    assert client.get('/health').json() == {'status': 'ok'}


def test_status_includes_indexing_failure_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(settings, "database_url", str(tmp_path / "test.db"))
    init_db()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO repositories (id, owner, name, url, branch, status, current_stage, progress, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("failed1", "owner", "repo", "https://github.com/owner/repo", "main", "failed", "failed", 0, "Branch does not exist."),
        )

    response = client.get("/api/repos/failed1/status")

    assert response.status_code == 200
    assert response.json()["error"] == "Branch does not exist."
