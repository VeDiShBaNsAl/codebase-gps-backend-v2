import os, shutil, subprocess
from fastapi import HTTPException
from app.config.settings import settings

EXCLUDED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next", "coverage", "vendor"}

def clone_repository(repo_url: str, branch: str, repo_id: str) -> str:
    dest_dir = os.path.join(settings.data_dir, "repos", repo_id)
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1", "--branch", branch, "--", repo_url, dest_dir]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=settings.clone_timeout_seconds, check=True)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=400, detail="Repository clone timed out.")
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {exc.stderr.strip()}")
    return dest_dir
