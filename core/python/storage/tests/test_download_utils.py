"""Tests for storage.download_utils module."""

import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from storage.download_utils import (
    download_and_extract_tar_gz,
    extract_tar_gz_archive,
)
from utils.utils_for_unit_tests import compare


def _write_tar_gz(path: Path, content: bytes, name: str = "hello.txt") -> None:
    with tarfile.open(path, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))


def test_extracttargzarchive_valid_uses_system_tar(tmp_path: Path) -> None:
    archive = tmp_path / "pkg.tar.gz"
    target_dir = tmp_path / "out"
    _write_tar_gz(archive, b"payload")

    with patch("storage.download_utils.shutil.which", return_value="/usr/bin/tar"):
        with patch("storage.download_utils.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            extract_tar_gz_archive(archive, target_dir)

    mock_run.assert_called_once_with(
        ["/usr/bin/tar", "-xzf", str(archive), "-C", str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_extracttargzarchive_valid_falls_back_to_python(tmp_path: Path) -> None:
    archive = tmp_path / "pkg.tar.gz"
    target_dir = tmp_path / "out"
    _write_tar_gz(archive, b"payload", name="nested/hello.txt")

    with patch("storage.download_utils.shutil.which", return_value=None):
        extract_tar_gz_archive(archive, target_dir)

    assert compare("eq", (target_dir / "nested/hello.txt").read_bytes(), b"payload")


def test_downloadandextracttargz_valid_downloads_then_extracts(tmp_path: Path) -> None:
    archive = tmp_path / "remote.tar.gz"
    target_dir = tmp_path / "extracted"
    _write_tar_gz(archive, b"stored", name="file.txt")

    def fake_download(_key: str, local_path: str) -> None:
        Path(local_path).write_bytes(archive.read_bytes())

    download_and_extract_tar_gz(fake_download, "some/key.tar.gz", target_dir)

    assert compare("eq", (target_dir / "file.txt").read_bytes(), b"stored")


def test_extracttargzarchive_invalid_missing_archive_raises(tmp_path: Path) -> None:
    with patch("storage.download_utils.shutil.which", return_value=None):
        with pytest.raises(FileNotFoundError):
            extract_tar_gz_archive(tmp_path / "missing.tar.gz", tmp_path / "out")
