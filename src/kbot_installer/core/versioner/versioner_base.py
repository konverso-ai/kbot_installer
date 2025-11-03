"""Base versioner class for full git operations.

This module defines the abstract base class that all versioners
must implement to provide a unified interface for full git operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)


class VersionerError(Exception):
    """Base exception for versioner-related errors.

    This exception is raised when versioner operations fail.
    """


class VersionerBase(ABC):
    """Abstract base class for versioners.

    This class defines the interface that all versioners must implement.
    It provides methods for full git operations: clone, add, pull, commit, and push.

    Attributes:
        name (str): Name of the versioner.
        base_url (str): Base URL of the versioner.

    """

    @abstractmethod
    def _get_auth(self) -> PyGitAuthenticationBase | None:
        """Get the authentication object for git operations.

        Returns:
            PyGitAuthenticationBase | None: The authentication object or None.

        """

    @abstractmethod
    def clone(self, repository_url: str, target_path: str | Path) -> None:
        """Clone a repository to the specified path.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.

        Raises:
            VersionerError: If the clone operation fails.

        """

    @abstractmethod
    def checkout(self, repository_path: str | Path, branch: str) -> None:
        """Checkout a specific branch in the repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """

    @abstractmethod
    def select_branch(
        self, repository_path: str | Path, branches: list[str]
    ) -> str | None:
        """Select the first available branch from a list of branches.

        This method attempts to checkout each branch in the provided list
        until it finds one that exists and can be checked out successfully.
        It stops at the first successful checkout and returns the branch name.

        Args:
            repository_path: Path to the local repository.
            branches: List of branch names to try in order.

        Returns:
            str | None: The name of the first successfully checked out branch,
                or None if no branch could be checked out.

        Raises:
            VersionerError: If there's an error with the repository or versioner.

        """

    @abstractmethod
    def add(
        self,
        repository_path: str | Path,
        files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area.

        Args:
            repository_path: Path to the local repository.
            files: List of files to add. If None, adds all changes.

        Raises:
            VersionerError: If the add operation fails.

        """

    @abstractmethod
    def pull(self, repository_path: str | Path, branch: str) -> None:
        """Pull latest changes from the remote repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Raises:
            VersionerError: If the pull operation fails.

        """

    @abstractmethod
    def commit(self, repository_path: str | Path, message: str) -> None:
        """Commit staged changes.

        Args:
            repository_path: Path to the local repository.
            message: Commit message.

        Raises:
            VersionerError: If the commit operation fails.

        """

    @abstractmethod
    def push(self, repository_path: str | Path, branch: str) -> None:
        """Push commits to the remote repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to push to.

        Raises:
            VersionerError: If the push operation fails.

        """

    @abstractmethod
    def stash(self, repository_path: str | Path, message: str | None = None) -> bool:
        """Stash current changes in the repository.

        Args:
            repository_path: Path to the local repository.
            message: Optional stash message. If None, uses default message.

        Returns:
            bool: True if changes were stashed, False if no changes to stash.

        Raises:
            VersionerError: If the stash operation fails.

        """

    @abstractmethod
    def safe_pull(self, repository_path: str | Path, branch: str) -> None:
        """Safely pull latest changes, stashing any local changes first.

        This method performs a safe pull by:
        1. Stashing any local changes
        2. Pulling the latest changes from remote
        3. Applying the stashed changes back

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Raises:
            VersionerError: If the safe pull operation fails.

        """

    @abstractmethod
    def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using the most efficient method.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            bool: True if repository exists, False otherwise.

        """
