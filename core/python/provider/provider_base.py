"""Base provider class for repository operations.

This module defines the abstract base class that all repository providers
must implement to provide a unified interface for git operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ProviderError(Exception):
    """Base exception for provider-related errors.

    This exception is raised when provider operations fail.
    """


class ProviderBase(ABC):
    """Abstract base class for repository providers.

    This class defines the interface that all repository providers must implement.
    It provides the clone method for downloading repositories.

    Attributes:
        base_url (str): Base URL of the provider.

    """

    @abstractmethod
    def clone_and_checkout(
        self, repository_url: str, target_path: str | Path, branch: str | None = None
    ) -> None:
        """Clone a repository to the specified path and optionally checkout a branch.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.

        Raises:
            ProviderError: If the clone operation fails.

        """

    @abstractmethod
    def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            bool: True if repository exists, False otherwise.

        """

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Name of the provider.

        """

    @abstractmethod
    def get_branch(self) -> str:
        """Get the branch of the provider.

        Returns:
            str: Branch of the provider.

        """
