"""Existing GitHub issue workflow, backed by the Person 4 investigation engine."""
import re

from fastapi import HTTPException

from app.models.schemas import IssueAnalyzeRequest
from app.services.github_client import GitHubClient
from app.services.intelligence_adapter import investigate_repository

ISSUE_URL = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/issues/(\d+)/?$")


async def analyze_issue(repo_id: str, payload: IssueAnalyzeRequest) -> dict:
    if payload.title:
        issue = {"title": payload.title, "description": payload.description}
    else:
        match = ISSUE_URL.match(payload.issue_url or "")
        if not match:
            raise HTTPException(status_code=400, detail="issue_url must be a GitHub /owner/repo/issues/number URL")
        owner, repository, number = match.groups()
        remote = await GitHubClient().get_issue(owner, repository, int(number))
        issue = {"number": remote["number"], "url": remote["html_url"], "title": remote["title"], "description": remote.get("body") or ""}
    report = investigate_repository(repo_id, issue)
    return {"issue": issue, "results": report["ranked_components"], "keywords": report["keywords"], "related_components": report["related_components"], "related_tests": report["related_tests"], "diagnostics": report["diagnostics"], "limitations": []}
