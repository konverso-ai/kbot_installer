"""Git operations mixin for providers.

This module provides a mixin class that contains common git operations
that can be shared across different repository providers.
"""

from pathlib import Path

from typing_extensions import override

from auth.base import HttpAuthBase
from auth.ssh_auth import SshAuth
from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.versioner import (
    VersionerBase,
    VersionerError,
    create_versioner,
)


class GitMixin(ProviderBase):
    """Mixin class providing common git operations for repository providers.

    This mixin provides the clone functionality using the versioner that can be
    shared across different repository providers like GitHub, Bitbucket, etc.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the GitMixin.

        Args:
            *args: Positional arguments passed to parent class.
            **kwargs: Keyword arguments passed to parent class.

        """
        super().__init__(*args, **kwargs)
        self._versioner: VersionerBase | None = None
        # Store the branch that was successfully used
        self.branch_used: str | None = None

    def _get_auth(self) -> HttpAuthBase | None:
        """Get authentication object for the provider.

        Returns:
            HttpAuthBase | None: Authentication object for the provider.

        """
        return None  # Default implementation returns None

    def _uses_ssh_auth(self) -> bool:
        """Return whether the provider is configured for SSH authentication."""
        return isinstance(self._get_auth(), SshAuth)

    def build_repository_url(self, repository_name: str) -> str:
        """Build the remote repository URL for the configured auth mode.

        Args:
            repository_name: Short repository name.

        Returns:
            HTTPS or SSH URL depending on the active authentication.

        Raises:
            ValueError: If the provider is missing URL template attributes.

        """
        account_name = getattr(self, "account_name", "")
        name = getattr(self, "name", "")
        base_url = getattr(self, "base_url", "")
        if not name or not account_name:
            msg = "Provider cannot build a repository URL"
            raise ValueError(msg)

        if self._uses_ssh_auth():
            ssh_host = getattr(self, "ssh_host", f"{name}.com")
            return f"git@{ssh_host}:{account_name}/{repository_name}.git"

        if not base_url:
            msg = "Provider cannot build a repository URL"
            raise ValueError(msg)
        return base_url.format(
            name=name,
            account_name=account_name,
            repository_name=repository_name,
        )

    def _get_versioner(self) -> VersionerBase:
        """Get or create the versioner instance.

        Returns:
            VersionerBase: The versioner instance.

        """
        if self._versioner is None:
            self._versioner = create_versioner("dulwich", auth=self._get_auth())
        return self._versioner

    def _perform_checkout(
        self,
        versioner: VersionerBase,
        target_path: str | Path,
        branch: str,
        repository_label: str,
    ) -> None:
        """Checkout a branch in a local repository.

        Args:
            versioner: Versioner instance to use.
            target_path: Path to the local repository.
            branch: Branch name to checkout.
            repository_label: Repository URL or path used in error messages.

        Raises:
            ProviderError: If checkout fails.

        """
        try:
            versioner.checkout(target_path, branch)
            self.branch_used = branch
        except VersionerError as e:
            error_str = str(e).lower()
            if "not found" in error_str or "branch" in error_str:
                error_msg = (
                    f"Branch '{branch}' not found for '{repository_label}' "
                    f"(repository cloned successfully). {e}"
                )
            else:
                error_msg = (
                    f"Failed to checkout branch '{branch}' for "
                    f"'{repository_label}': {e}"
                )
            raise ProviderError(error_msg) from e

    def list_remote_branches(self, repository_url: str) -> list[str]:
        """List branches available on the remote repository.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            Branch names reported by the versioner.

        Raises:
            ProviderError: If the remote cannot be queried.

        """
        versioner = self._get_versioner()
        try:
            return versioner.list_remote_branches(repository_url)
        except VersionerError as e:
            error_msg = f"Failed to list remote branches for '{repository_url}': {e}"
            raise ProviderError(error_msg) from e

    def checkout_branch(self, target_path: str | Path, branch: str) -> None:
        """Checkout a branch in an already cloned repository.

        Args:
            target_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            ProviderError: If checkout fails.

        """
        versioner = self._get_versioner()
        self._perform_checkout(versioner, target_path, branch, str(target_path))

    @override
    def clone_and_checkout(
        self,
        target_path: str | Path,
        branch: str | None = None,
        *,
        repository_url: str | None = None,
        repository_name: str | None = None,
    ) -> None:
        """Clone a repository to the specified path and optionally checkout a branch.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.
            repository_url: URL of the repository to clone.
            repository_name: Unused by the git mixin.

        Raises:
            ProviderError: If the clone operation fails.

        """
        if not repository_url:
            msg = "repository_url is required"
            raise ValueError(msg)
        try:
            versioner = self._get_versioner()
            if branch:
                versioner.clone(
                    repository_url,
                    target_path,
                    branch=branch,
                    depth=1,
                )
                self.branch_used = branch
            else:
                versioner.clone(repository_url, target_path)
                self.branch_used = None
        except ProviderError:
            raise
        except VersionerError as e:
            error_msg = f"Failed to clone repository '{repository_url}': {e}"
            raise ProviderError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error while cloning repository '{repository_url}': {e}"
            )
            raise ProviderError(error_msg) from e

    @override
    def get_branch(self) -> str:
        """Get the branch of the provider.

        Returns:
            str: Branch of the provider. Returns empty string if no branch was used.

        """
        return self.branch_used or ""
