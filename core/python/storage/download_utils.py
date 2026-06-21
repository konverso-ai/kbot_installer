"""Shared helpers for storage download operations."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable
from pathlib import Path

from installer_support.installer_utils import extract_tar_member

logger = logging.getLogger(__name__)


def extract_tar_gz_archive(archive_path: Path, target_dir: Path) -> None:
    """Extract a ``.tar.gz`` archive, preferring the system ``tar`` when available."""
    target_dir.mkdir(parents=True, exist_ok=True)
    tar_bin = shutil.which("tar")
    if tar_bin is not None:
        result = subprocess.run(
            [tar_bin, "-xzf", str(archive_path), "-C", str(target_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return

        details = (result.stderr or result.stdout or "").strip()
        logger.warning(
            "System tar extraction failed (exit %s), falling back to Python: %s",
            result.returncode,
            details,
        )

    _extract_tar_gz_with_python(archive_path, target_dir)


def _extract_tar_gz_with_python(archive_path: Path, target_dir: Path) -> None:
    """Extract a ``.tar.gz`` archive with Python tarfile and symlink handling."""
    with tarfile.open(archive_path, mode="r:gz") as tar:
        for member in tar:
            extract_tar_member(tar, member, target_dir)


def download_and_extract_tar_gz(
    download_file: Callable[[str, str], None],
    key: str,
    target_dir: Path,
) -> None:
    """Download a tar.gz object to a temporary file and extract it."""
    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as temp_file:
        temp_path = temp_file.name

    try:
        download_file(key, temp_path)
        extract_tar_gz_archive(Path(temp_path), target_dir)
    finally:
        Path(temp_path).unlink(missing_ok=True)
