from pathlib import Path


def ensure_path(path: str | Path) -> Path:
    """Ensure a path exists."""
    return Path(path).resolve()


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists."""
    directory = ensure_path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_file_path(path: str | Path) -> Path:
    """Ensure parent directories exist for a file path."""
    file_path = ensure_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path
