"""Tests for utils.path_utils module."""

from pathlib import Path

from utils.path_utils import ensure_directory, ensure_file_path, ensure_path
from utils.utils_for_unit_tests import compare


def test_ensurepath_valid_resolves_existing_path(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir"
    target.mkdir(parents=True)
    assert compare("eq", ensure_path(target), target.resolve())


def test_ensuredirectory_valid_creates_missing_directories(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir"
    created = ensure_directory(target)
    assert compare("eq", created.exists(), True)
    assert compare("eq", created.is_dir(), True)


def test_ensurefilepath_valid_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "file.txt"
    file_path = ensure_file_path(target)
    assert compare("eq", file_path.parent.exists(), True)
    assert compare("eq", file_path, target.resolve())
