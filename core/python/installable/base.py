"""Base interface for installable products."""

from abc import ABC, abstractmethod
from pathlib import Path


class InstallableBase(ABC):
    """Base interface for installable products.

    This interface defines the contract that all installable products must implement.
    """

    @abstractmethod
    def download(self, path: Path) -> None:
        """Download the product to the given path.

        Args:
            path: Path to download the product to.

        """
