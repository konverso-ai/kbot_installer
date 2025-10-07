"""Git operations mixin for providers.

This module provides a mixin class that contains common git operations
that can be shared across different repository providers.
"""

from pathlib import Path

from kbot_installer.core.provider.provider_base import ProviderBase, ProviderError
from kbot_installer.core.versioner import (
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
        self._versioner = None

    def _get_auth(self) -> object:
        """Get authentication object for the provider.

        Returns:
            object: Authentication object specific to the provider type.

        """
        return None  # Default implementation returns None

    def _get_versioner(self) -> VersionerBase:
        """Get or create the versioner instance.

        Returns:
            VersionerBase: The versioner instance.

        """
        if self._versioner is None:
            self._versioner = create_versioner("pygit", auth=self._get_auth())
        return self._versioner

    async def clone_and_checkout(
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
        try:
            versioner = self._get_versioner()
            await versioner.clone(repository_url, target_path)

            # If a specific branch is requested, checkout that branch
            if branch:
                try:
                    await versioner.checkout(target_path, branch)
                except VersionerError as e:
                    # Check if this is a branch not found error
                    if "not found" in str(e).lower() or "branch" in str(e).lower():
                        error_msg = f"Version '{branch}' not found for repository '{repository_url}'. {e}"
                    else:
                        error_msg = f"Failed to checkout branch '{branch}' for repository '{repository_url}': {e}"
                    raise ProviderError(error_msg) from e
        except VersionerError as e:
            # This is a clone error, not a checkout error
            error_msg = f"Failed to clone repository '{repository_url}': {e}"
            raise ProviderError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            raise ProviderError(error_msg) from e
