"""Utility functions for file downloading and extraction.

This module provides utilities for downloading and extracting tar.gz files.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
