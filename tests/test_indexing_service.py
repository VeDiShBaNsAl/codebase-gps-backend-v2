import asyncio
import subprocess

import pytest
from fastapi import BackgroundTasks

from app.api.repos import index_repository
from app.config.settings import settings
from app.database.db import get_db_connection, init_db
from app.models.graph import GraphNode
from app.models.schemas import IndexRequest
from app.services import indexing_service, ingestion_service


def test_indexing_completes_without_opening_a_second_write_transaction(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(settings, "database_url", str(tmp_path / "test.db"))
    init_db()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO repositories (id, owner, name, url, branch, status, current_stage, progress) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("repo1", "owner", "repo", "https://github.com/owner/repo", "main", "queued", "queued", 0),
        )

    node = GraphNode(id="function-run", type="FUNCTION", name="run", file_path="main.py", start_line=1, end_line=2, language="python")
    monkeypatch.setattr(indexing_service, "clone_repository", lambda *_: str(tmp_path / "repo"))
    monkeypatch.setattr(indexing_service, "analyze_repository", lambda _: {
        "nodes": [node], "edges": [], "languages": ["python"], "total_files": 1, "total_symbols": 1, "total_relationships": 0,
    })

    indexing_service.run_indexing_pipeline("repo1", "https://github.com/owner/repo", "main")

    with get_db_connection() as conn:
        repo = conn.execute("SELECT status, progress FROM repositories WHERE id = 'repo1'").fetchone()
        symbols = conn.execute("SELECT COUNT(*) AS count FROM symbols_fts WHERE repo_id = 'repo1'").fetchone()
    assert dict(repo) == {"status": "completed", "progress": 100}
    assert symbols["count"] == 1


def test_index_request_reuses_an_in_progress_job(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(settings, "database_url", str(tmp_path / "test.db"))
    init_db()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO repositories (id, owner, name, url, branch, status, current_stage, progress) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("existing", "owner", "repo", "https://github.com/owner/repo", "main", "processing", "cloning", 10),
        )

    tasks = BackgroundTasks()
    response = asyncio.run(index_repository(IndexRequest(repo_url="https://github.com/owner/repo", branch="main"), tasks))

    assert response.repo_id == "existing"
    assert response.status == "processing"
    assert not tasks.tasks


def test_clone_disables_interactive_git_prompts_and_uses_shallow_clone(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    calls = {}

    def run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs

    monkeypatch.setattr(ingestion_service.subprocess, "run", run)

    destination = ingestion_service.clone_repository("https://github.com/owner/repo", "main", "repo1")

    assert destination == str(tmp_path / "repos" / "repo1")
    assert "--single-branch" in calls["command"]
    assert "--no-tags" in calls["command"]
    assert "--filter=blob:none" in calls["command"]
    assert calls["kwargs"]["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert calls["kwargs"]["env"]["GIT_ASKPASS"] == "/bin/false"


def test_clone_removes_partial_checkout_after_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("git clone", 1)

    monkeypatch.setattr(ingestion_service.subprocess, "run", timeout)

    with pytest.raises(Exception, match="Repository clone timed out"):
        ingestion_service.clone_repository("https://github.com/owner/repo", "main", "repo1")

    assert not (tmp_path / "repos" / "repo1").exists()    
