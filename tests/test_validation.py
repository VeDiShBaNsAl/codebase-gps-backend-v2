import pytest
from fastapi import HTTPException
from app.services.repo_validation import validate_repo_url, validate_branch

def test_valid_repo_urls():
    owner, repo, norm = validate_repo_url("https://github.com/fastapi/fastapi")
    assert owner == "fastapi"
    assert repo == "fastapi"
    assert norm == "https://github.com/fastapi/fastapi"

def test_invalid_repo_urls():
    with pytest.raises(HTTPException):
        validate_repo_url("http://gitlab.com/owner/repo")

def test_valid_branches():
    assert validate_branch("main") == "main"

def test_malicious_branches():
    with pytest.raises(HTTPException):
        validate_branch("-b")
