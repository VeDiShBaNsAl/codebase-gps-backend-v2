import os, shutil, subprocess
from fastapi import HTTPException
from app.config.settings import settings

EXCLUDED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".next", "coverage", "vendor"}

def clone_repository(repo_url: str, branch: str, repo_id: str) -> str:
    dest_dir = os.path.join(settings.data_dir, "repos", repo_id)
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    # Render background workers have no TTY. Disable Git credential prompts so
    # an unavailable or private remote fails instead of appearing stuck at 10%.
    cmd = [
        "git", "-c", "credential.interactive=false", "clone",
        "--depth", "1", "--single-branch", "--no-tags",
        "--filter=blob:none", "--branch", branch, "--", repo_url, dest_dir,
    ]
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "/bin/false"
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=settings.clone_timeout_seconds,
            check=True,
            env=env,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Repository clone timed out.")
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {exc.stderr.strip()}")
    return dest_dir
