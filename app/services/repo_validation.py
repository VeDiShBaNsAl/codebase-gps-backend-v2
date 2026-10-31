import re
from fastapi import HTTPException, status

URL_REGEX = re.compile(r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)(?:\.git)?$")
BRANCH_REGEX = re.compile(r"^[a-zA-Z0-9_./-]+$")

def validate_repo_url(repo_url: str) -> tuple[str, str, str]:
    if not repo_url or not isinstance(repo_url, str):
        raise HTTPException(status_code=400, detail="Repository URL must be a non-empty string.")
    cleaned_url = repo_url.strip()
    if cleaned_url.endswith("/"):
        cleaned_url = cleaned_url[:-1]
    match = URL_REGEX.match(cleaned_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid repository URL. Must match https://github.com/{owner}/{repo}")
    owner, repo = match.groups()
    return owner, repo, f"https://github.com/{owner}/{repo}"

def validate_branch(branch: str) -> str:
    if not branch or not isinstance(branch, str):
        raise HTTPException(status_code=400, detail="Branch name must be a non-empty string.")
    cleaned_branch = branch.strip()
    if cleaned_branch.startswith("-") or ".." in cleaned_branch or any(c in cleaned_branch for c in " \t\n\r;|&`$()<>\\['\"]"):
        raise HTTPException(status_code=400, detail="Invalid branch name format or potential security risk.")
    if not BRANCH_REGEX.match(cleaned_branch):
        raise HTTPException(status_code=400, detail="Branch name contains unsupported characters.")
    return cleaned_branch
