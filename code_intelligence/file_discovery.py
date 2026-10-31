"""Safe, deterministic source-file discovery."""
from __future__ import annotations

from pathlib import Path

SUPPORTED_SUFFIXES = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript"}
IGNORED_DIRECTORIES = {".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__", "build", "dist", ".next", "coverage"}


def discover_source_files(repository_path: str) -> list[Path]:
    """Return supported files beneath *repository_path*, excluding generated trees."""
    root = Path(repository_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {repository_path}")
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix())


def language_for(path: Path) -> str:
    return SUPPORTED_SUFFIXES[path.suffix.lower()]
