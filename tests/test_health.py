from fastapi.testclient import TestClient
from app.main import app
from app.config.settings import settings
from app.database.db import get_db_connection, init_db
client = TestClient(app)


def test_health():
    assert client.get('/health').json() == {'status': 'ok'}


def test_root_identifies_the_api_and_documents_available_routes():
    assert client.get("/").json() == {
        "service": "Codebase GPS API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }


def test_vercel_frontend_origin_is_allowed_for_preflight_requests():
    response = client.options(
        "/api/repos/index",
        headers={
            "Origin": "https://codebase-gps-backend-v2.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://codebase-gps-backend-v2.vercel.app"


def test_vercel_origin_is_preserved_on_an_unhandled_api_error():
    def raise_unhandled_error():
        raise RuntimeError("simulated investigation failure")

    app.app.add_api_route("/_test/unhandled-error", raise_unhandled_error)
    error_client = TestClient(app, raise_server_exceptions=False)

    response = error_client.get(
        "/_test/unhandled-error",
        headers={"Origin": "https://codebase-gps-backend-v2.vercel.app"},
    )

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "https://codebase-gps-backend-v2.vercel.app"


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
