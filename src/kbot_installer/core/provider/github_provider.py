"""GitHub provider for repository operations.

This module implements the GithubProvider class that handles repository
operations specific to GitHub repositories. It supports cloning repositories
from GitHub using pygit2.
"""

import logging
from pathlib import Path

from kbot_installer.core.auth.pygit_authentication import PyGitAuthenticationBase
from kbot_installer.core.provider.git_mixin import GitMixin

logger = logging.getLogger(__name__)


class GithubProvider(GitMixin):
    """Provider for GitHub repository operations.

    This provider handles operations on GitHub repositories. Currently,
    it implements the clone operation using git commands.

    Attributes:
        base_url (str): Base URL of the GitHub instance.
        account_name (str): Name of the GitHub account.
        auth (PyGitAuthenticationBase | None): PyGit authentication object.

    """

    name = "github"
    base_url = "https://{name}.com/{account_name}/{repository_name}.git"

    def __init__(
        self,
        account_name: str,
        auth: PyGitAuthenticationBase | None = None,
    ) -> None:
        """Initialize the GitHub provider.

        Args:
            account_name: Name of the GitHub account.
            auth: PyGit authentication object for repository operations.
                If None, operations will use public access only.

        """
        logger.debug("Initializing GitHub provider with account name: %s", account_name)
        super().__init__()
        self.account_name = account_name
        self._auth = auth

    def _get_auth(self) -> PyGitAuthenticationBase | None:
        """Get authentication object for GitHub.

        Returns:
            PyGitAuthenticationBase | None: Authentication object for GitHub operations.

        """
        return self._auth

    def clone_and_checkout(
        self, repository_name: str, target_path: str | Path, branch: str | None = None
    ) -> None:
        """Clone a repository from GitHub and optionally checkout a branch.

        Args:
            repository_name: Name of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.

        Raises:
            ProviderError: If the clone operation fails.

        """
        repository_url = self.base_url.format(
            name=self.name,
            account_name=self.account_name,
            repository_name=repository_name,
        )
        # Use the parent clone_and_checkout method which handles authentication
        super().clone_and_checkout(repository_url, target_path, branch)

    def check_remote_repository_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists on GitHub.

        Args:
            repository_name: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            repository_url = self.base_url.format(
                name=self.name,
                account_name=self.account_name,
                repository_name=repository_name,
            )
            # Use the versioner to check if repository exists
            versioner = self._get_versioner()
            return versioner.check_remote_repository_exists(repository_url)
        except Exception:
            return False

    def get_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Name of the provider.

        """
        return self.name
