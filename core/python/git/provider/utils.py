"""Utility functions for file downloading and extraction.

This module provides utilities for downloading and extracting tar.gz files.
"""

from dataclasses import dataclass

from utils.Logger import logger

log = logger.get_package_logger("git.provider")


@dataclass
class FileInfo:
    """Information about a file to download."""

    name: str  # Product name (e.g., "3rdparty")
    host: str
    repository: str
    branch: str
    size: int = 0
    temp_path: str = ""

    @property
    def url(self) -> str:
        """Automatically generate URL from parameters."""
        return f"https://{self.host}/repository/{self.repository}/{self.branch}/{self.name}/{self.name}_latest.tar.gz"

    @property
    def filename(self) -> str:
        """Complete filename for display."""
        return f"{self.name}_latest.tar.gz"


def build_object_key(repository_name: str, branch: str | None, commit_id: str | None = None) -> str:
    """Build the object key for a repository archive.

    Args:
        repository_name: Name of the repository/product.
        branch: Branch the archive was built from. Defaults to "master".
        commit_id: Commit to pin the archive to. If None, the "latest" archive
            for the branch is targeted instead.

    Returns:
        The object key identifying the archive in storage.

    """
    branch_name = branch or "master"
    suffix = commit_id or "latest"
    return f"{branch_name}/{repository_name}/{repository_name}_{suffix}.tar.gz"
