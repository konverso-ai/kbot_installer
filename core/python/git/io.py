from pathlib import Path

from git.models import GitRepo
from utils.path_utils import ensure_file_path


def write_repository(repo: GitRepo, root: str | Path) -> None:
    """Write repository files to disk."""
    for path, content in repo.export().items():
        ensure_file_path(path).write_text(content, encoding="utf-8")
