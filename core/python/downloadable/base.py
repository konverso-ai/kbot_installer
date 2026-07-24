"""Base interface for downloadable entities."""

from abc import ABC, abstractmethod
from pathlib import Path


class DownloadableBase(ABC):
    """Interface for entities that can be downloaded to a local path."""

    @abstractmethod
    def download(self, path: Path | str) -> None:
        """Download the entity into path.

        Args:
            path: Directory the entity should be downloaded into.

        """
