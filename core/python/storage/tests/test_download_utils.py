"""Tests for storage.download_utils module."""

import io
import shutil
import tarfile
from collections.abc import Callable
from pathlib import Path
from typing import IO
from unittest.mock import MagicMock, patch

import pytest

from storage.download_utils import (
    SystemTarError,
    download_and_extract_tar_gz,
    extract_tar_gz_archive,
    system_tar_gz_extractor,
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


def _fake_download(archive: Path) -> Callable[[str, IO[bytes]], None]:
    def download_to(_key: str, stream: IO[bytes]) -> None:
        stream.write(archive.read_bytes())

    return download_to


@pytest.mark.skipif(shutil.which("tar") is None, reason="system tar is required")
def test_downloadandextracttargz_valid_streams_into_system_tar(tmp_path: Path) -> None:
    archive = tmp_path / "remote.tar.gz"
    target_dir = tmp_path / "extracted"
    _write_tar_gz(archive, b"stored", name="nested/file.txt")

    with patch("storage.download_utils._extract_tar_gz_with_python") as python_extract:
        download_and_extract_tar_gz(_fake_download(archive), "some/key.tar.gz", target_dir)

    python_extract.assert_not_called()
    assert compare("eq", (target_dir / "nested/file.txt").read_bytes(), b"stored")


def test_downloadandextracttargz_valid_without_tar_uses_python(tmp_path: Path) -> None:
    archive = tmp_path / "remote.tar.gz"
    target_dir = tmp_path / "extracted"
    _write_tar_gz(archive, b"stored", name="file.txt")

    with patch("storage.download_utils.shutil.which", return_value=None):
        download_and_extract_tar_gz(_fake_download(archive), "some/key.tar.gz", target_dir)

    assert compare("eq", (target_dir / "file.txt").read_bytes(), b"stored")


@pytest.mark.skipif(shutil.which("false") is None, reason="false command is required")
def test_downloadandextracttargz_valid_tar_failure_falls_back_to_python(tmp_path: Path) -> None:
    archive = tmp_path / "remote.tar.gz"
    target_dir = tmp_path / "extracted"
    _write_tar_gz(archive, b"stored", name="file.txt")
    download_to = MagicMock(side_effect=_fake_download(archive))

    with patch("storage.download_utils.shutil.which", return_value=shutil.which("false")):
        download_and_extract_tar_gz(download_to, "some/key.tar.gz", target_dir)

    assert compare("eq", download_to.call_count, 2)
    assert compare("eq", (target_dir / "file.txt").read_bytes(), b"stored")


@pytest.mark.skipif(shutil.which("tar") is None, reason="system tar is required")
def test_downloadandextracttargz_invalid_download_error_propagates(tmp_path: Path) -> None:
    def failing_download(_key: str, stream: IO[bytes]) -> None:
        stream.write(b"partial")
        msg = "network down"
        raise ConnectionError(msg)

    with pytest.raises(ConnectionError, match="network down"):
        download_and_extract_tar_gz(failing_download, "some/key.tar.gz", tmp_path / "out")


@pytest.mark.skipif(shutil.which("tar") is None, reason="system tar is required")
def test_systemtargzextractor_invalid_archive_raises(tmp_path: Path) -> None:
    tar_bin = shutil.which("tar")
    assert tar_bin is not None

    with pytest.raises(SystemTarError):
        with system_tar_gz_extractor(tar_bin, tmp_path) as stream:
            stream.write(b"not a gzip archive")


def test_extracttargzarchive_invalid_missing_archive_raises(tmp_path: Path) -> None:
    with patch("storage.download_utils.shutil.which", return_value=None):
        with pytest.raises(FileNotFoundError):
            extract_tar_gz_archive(tmp_path / "missing.tar.gz", tmp_path / "out")
