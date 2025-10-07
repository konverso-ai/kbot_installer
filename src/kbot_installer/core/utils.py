"""Utility functions for kbot-installer."""

import logging
import tarfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def version_to_branch(version: str) -> str:
    """Convert a version string to a Git branch name.

    Args:
        version: Version string (e.g., '2025.03', 'dev', 'master', '2025.03-dev').

    Returns:
        Git branch name corresponding to the version.

    Examples:
        >>> version_to_branch("dev")
        "dev"
        >>> version_to_branch("master")
        "master"
        >>> version_to_branch("2025.03")
        "release-2025.03"
        >>> version_to_branch("2025.03-dev")
        "release-2025.03-dev"

    """
    if version == "dev":
        return "dev"
    if version == "master":
        return "master"
    if version.endswith("-dev"):
        # 2025.03-dev → release-2025.03-dev
        base_version = version[:-4]  # Remove "-dev"
        return f"release-{base_version}-dev"
    # 2025.03 → release-2025.03
    return f"release-{version}"


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory.

    Returns:
        Path object of the directory.

    Raises:
        OSError: If the directory cannot be created.

    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def optimized_download_and_extract(
    url: str, target_dir: Path, auth_obj: object | None = None
) -> None:
    """Optimized download and extract using benchmark results.

    Uses the most efficient method: streaming download with 4MB chunks
    and direct extraction without temporary file when possible.

    Args:
        url: URL to download the tar.gz file from.
        target_dir: Target directory for extraction.
        auth_obj: Authentication object for download.

    Raises:
        httpx.HTTPError: If the HTTP request fails.
        tarfile.TarError: If the tar file is corrupted or invalid.
        OSError: If there are issues with file system operations during extraction.

    """
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    # Stream download and extract in one pass (most efficient method)
    with httpx.stream("GET", url, timeout=60.0, auth=auth_obj) as response:
        response.raise_for_status()

        # Create tarfile from stream with optimal chunk size (4MB from benchmark)
        with tarfile.open(
            fileobj=response.iter_bytes(chunk_size=16 * 1024 * 1024), mode="r|gz"
        ) as tar:
            for member in tar:
                tar.extract(member, path=target_dir, filter="data")

    logger.info(
        "Successfully downloaded and extracted from %s to %s",
        url,
        target_dir,
    )
