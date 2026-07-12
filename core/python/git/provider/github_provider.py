"""GitHub provider for repository operations.

This module implements the GithubProvider class that handles repository
operations specific to GitHub repositories. It supports cloning repositories
from GitHub using dulwich.
"""

from pathlib import Path

from typing_extensions import override

from auth.base import HttpAuthBase
from git.provider.git_mixin import GitMixin
from utils.Logger import logger

log = logger.get_package_logger("git.provider")


class GithubProvider(GitMixin):
    """Provider for GitHub repository operations.

    This provider handles operations on GitHub repositories. Currently,
    it implements the clone operation using git commands.

    Attributes:
        base_url (str): Base URL of the GitHub instance.
        account_name (str): Name of the GitHub account.
        auth (HttpAuthBase | None): Authentication object for repository operations.

    """

    name = "github"
    ssh_host = "github.com"
    base_url = "https://{name}.com/{account_name}/{repository_name}.git"

    def __init__(
        self,
        account_name: str,
        auth: HttpAuthBase | None = None,
    ) -> None:
        """Initialize the GitHub provider.

        Args:
            account_name: Name of the GitHub account.
            auth: PyGit authentication object for repository operations.
                If None, operations will use public access only.

        """
        log.debug("Initializing GitHub provider with account name: %s", account_name)
        super().__init__()
        self.account_name = account_name
        self._auth = auth

    @override
    def _get_auth(self) -> HttpAuthBase | None:
        """Get authentication object for GitHub.

        Returns:
            HttpAuthBase | None: Authentication object for GitHub operations.

        """
        return self._auth

    @override
    def clone_and_checkout(
        self,
        target_path: str | Path,
        branch: str | None = None,
        *,
        repository_url: str | None = None,
        repository_name: str | None = None,
    ) -> None:
        """Clone a repository from GitHub and optionally checkout a branch.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.
            repository_url: Unused by the GitHub provider.
            repository_name: Name of the repository to clone.

        Raises:
            ProviderError: If the clone operation fails.

        """
        if repository_name is None:
            msg = "repository_name is required"
            raise ValueError(msg)
        repository_url = self.build_repository_url(repository_name)
        super().clone_and_checkout(target_path, branch, repository_url=repository_url)

    @override
    def check_remote_repository_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists on GitHub.

        Args:
            repository_name: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            repository_url = self.build_repository_url(repository_name)
            # Use the versioner to check if repository exists
            versioner = self._get_versioner()
            return versioner.remote_exists(repository_url)
        except Exception:
            return False

    @override
    def get_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Name of the provider.

        """
        return self.name
