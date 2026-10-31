import httpx
from fastapi import HTTPException
from app.config.settings import settings

class GitHubClient:
    def __init__(self):
        self.headers = {"Accept": "vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if settings.github_token:
            self.headers["Authorization"] = f"Bearer {settings.github_token}"

    async def get_repo_metadata(self, owner: str, repo: str) -> dict:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
            except httpx.RequestError as exc:
                raise HTTPException(status_code=502, detail=f"Failed to communicate with GitHub API: {exc}")
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Repository not found or is private.")
            elif response.status_code in (403, 429):
                raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded or access forbidden.")
            elif response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"GitHub API error: {response.status_code}")
            return response.json()

    async def get_issue(self, owner: str, repo: str, number: int) -> dict:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self.headers)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="GitHub issue not found.")
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"GitHub API error: {response.status_code}")
        return response.json()
