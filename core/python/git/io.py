from pathlib import Path

from git.models import GitRepo
from utils.path_utils import ensure_file_path


def write_repository(repo: GitRepo, root: str | Path) -> None:
    """Write repository files to disk under the given root directory."""
    root_path = Path(root).resolve()
    for relative_path, content in repo.export().items():
        file_path = ensure_file_path(root_path / relative_path)
        file_path.write_text(content, encoding="utf-8")
