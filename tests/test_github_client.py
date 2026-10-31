import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app.services.github_client import GitHubClient


class TimeoutClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        raise httpx.ReadTimeout("GitHub did not respond")


def test_get_issue_returns_a_clear_gateway_error_when_github_times_out(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: TimeoutClient())

    with pytest.raises(HTTPException) as error:
        asyncio.run(GitHubClient().get_issue("owner", "repo", 1))

    assert error.value.status_code == 502
    assert error.value.detail.startswith("Failed to communicate with GitHub API:")
