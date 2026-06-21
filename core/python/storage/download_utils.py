"""Shared helpers for storage download operations."""

from __future__ import annotations

import tarfile
import tempfile
from collections.abc import Callable
from pathlib import Path

from installer_support.installer_utils import extract_tar_member


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
        with tarfile.open(temp_path, mode="r:gz") as tar:
            for member in tar:
                extract_tar_member(tar, member, target_dir)
    finally:
        Path(temp_path).unlink(missing_ok=True)
