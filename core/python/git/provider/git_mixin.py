"""Git operations mixin for providers.

This module provides a mixin class that contains common git operations
that can be shared across different repository providers.
"""

from pathlib import Path

from auth.base import HttpAuthBase
from typing_extensions import override
from git.versioner import (
    VersionerBase,
    VersionerError,
    create_versioner,
)

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError


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

    def _get_versioner(self) -> VersionerBase:
        """Get or create the versioner instance.

        Returns:
            VersionerBase: The versioner instance.

        """
        if self._versioner is None:
            self._versioner = create_versioner("dulwich", auth=self._get_auth())
        return self._versioner

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
            versioner.clone(repository_url, target_path)

            # If a specific branch is requested, checkout that branch
            if branch:
                try:
                    versioner.checkout(target_path, branch)
                    # Store the branch that was successfully used
                    self.branch_used = branch
                except VersionerError as e:
                    # Check if this is a branch not found error
                    if "not found" in str(e).lower() or "branch" in str(e).lower():
                        error_msg = f"Version '{branch}' not found for repository '{repository_url}'. {e}"
                    else:
                        error_msg = f"Failed to checkout branch '{branch}' for repository '{repository_url}': {e}"
                    raise ProviderError(error_msg) from e
            else:
                # If no branch specified, use default branch (typically "main" or "master")
                # We'll need to detect it, but for now store None
                self.branch_used = None
        except VersionerError as e:
            # This is a clone error, not a checkout error
            error_msg = f"Failed to clone repository '{repository_url}': {e}"
            raise ProviderError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            raise ProviderError(error_msg) from e

    @override
    def get_branch(self) -> str:
        """Get the branch of the provider.

        Returns:
            str: Branch of the provider. Returns empty string if no branch was used.

        """
        return self.branch_used or ""
