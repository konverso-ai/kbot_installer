"""Bitbucket provider for repository operations.

This module implements the BitbucketProvider class that handles repository
operations specific to Bitbucket repositories. It supports cloning repositories
from Bitbucket using Dulwich.
"""

from pathlib import Path

from auth.base import HttpAuthBase

from git.provider.git_mixin import GitMixin
from typing_extensions import override


class BitbucketProvider(GitMixin):
    """Provider for Bitbucket repository operations.

    This provider handles operations on Bitbucket repositories. Currently,
    it implements the clone operation using git commands.

    Attributes:
        base_url (str): Base URL of the Bitbucket instance.
        account_name (str): Name of the Bitbucket account.
        auth (HttpAuthBase | None): Authentication object for repository operations.

    """

    name = "bitbucket"
    base_url = "https://{name}.org/{account_name}/{repository_name}.git"

    def __init__(
        self,
        account_name: str,
        auth: HttpAuthBase | None = None,
        **kwargs,  # noqa: ARG002, ANN003
    ) -> None:
        """Initialize the Bitbucket provider.

        Args:
            account_name: Name of the Bitbucket account.
            auth: PyGit authentication object for repository operations.
                If None, operations will use public access only.
            **kwargs: Additional arguments (ignored).

        """
        super().__init__()
        self.account_name = account_name
        self._auth = auth

    @override
    def _get_auth(self) -> HttpAuthBase | None:
        """Get authentication object for Bitbucket.

        Returns:
            HttpAuthBase | None: Authentication object for Bitbucket operations.

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
        """Clone a repository from Bitbucket and optionally checkout a branch.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.
            repository_url: Unused by the Bitbucket provider.
            repository_name: Name of the repository to clone.

        Raises:
            ProviderError: If the clone operation fails.

        """
        if repository_name is None:
            msg = "repository_name is required"
            raise ValueError(msg)
        repository_url = self.base_url.format(
            name=self.name,
            account_name=self.account_name,
            repository_name=repository_name,
        )
        # Use the parent clone_and_checkout method which handles authentication
        super().clone_and_checkout(
            target_path, branch, repository_url=repository_url
        )

    @override
    def check_remote_repository_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists on Bitbucket.

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
