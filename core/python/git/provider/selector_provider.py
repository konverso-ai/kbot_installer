"""Selector provider for automatic provider selection.

This module implements the SelectorProvider class that automatically selects
the appropriate provider based on repository availability. It tries multiple
already-built provider instances in sequence until it finds one that has the
repository, delegating per-provider branch fallback to
:mod:`git.provider.branch_resolver`.
"""

from pathlib import Path

from typing_extensions import override

from git.provider.base import ProviderBase
from git.provider.branch_resolver import clone_with_branch_fallback, get_branches_to_try
from git.provider.errors import ProviderError
from utils.Logger import logger

log = logger.get_package_logger("git.provider")


class SelectorProvider(ProviderBase):
    """Provider that automatically selects the appropriate provider.

    This provider tries each given provider instance in order. The first one
    that succeeds wins; if all fail, a single ``ProviderError`` is raised
    listing every provider's failure reason.

    Attributes:
        providers (list[ProviderBase]): Provider instances to try in order.

    """

    name = ""

    def __init__(
        self,
        providers: list[ProviderBase],
        *,
        quiet: bool = False,
    ) -> None:
        """Initialize the selector provider.

        Args:
            providers: Provider instances to try in order (e.g., storage,
                github, bitbucket providers already built and configured).
            quiet: When True, suppress informational clone output.

        """
        self.providers = providers
        self.quiet = quiet
        # Branch used by the provider that last succeeded.
        self.__branch_used: str | None = None

    def _update_provider_name(self, provider: ProviderBase) -> None:
        """Record the name reported by the provider that just succeeded.

        Args:
            provider: Provider instance to get the name from.

        """
        try:
            if hasattr(provider, "get_name") and callable(getattr(provider, "get_name", None)):
                self.name = provider.get_name()
        except Exception as e:
            # Log but ignore errors when getting provider name.
            log.debug("Failed to get provider name: %s", type(e).__name__)

    @override
    def clone_and_checkout(
        self,
        repository_name: str,
        target_path: str | Path,
        *,
        branch: str | None = None,
        commit_id: str | None = None,
    ) -> None:
        """Clone a repository using the first available provider.

        Args:
            repository_name: Name of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.
            commit_id: Specific commit to pin the checkout to. Only honored by providers
                that support commit pinning (e.g. storage-backed providers); ignored
                by plain git providers.

        Raises:
            ProviderError: If all providers fail to clone the repository.

        """
        target_path = Path(target_path)
        target_path.mkdir(parents=True, exist_ok=True)

        failures: list[tuple[str, str]] = []
        for provider in self.providers:
            branches = get_branches_to_try(getattr(provider, "branches", []), branch)
            try:
                self.__branch_used = clone_with_branch_fallback(
                    provider,
                    repository_name,
                    target_path,
                    branches,
                    commit_id=commit_id,
                )
            except ProviderError as e:
                failures.append((str(provider), str(e)))
                continue
            except Exception as e:
                failures.append((str(provider), f"Unexpected error: {type(e).__name__}: {e}"))
                continue

            self._update_provider_name(provider)
            log_fn = log.debug if self.quiet else log.info
            log_fn(
                "Successfully cloned repository '%s' using provider: %s (branch: %s)",
                repository_name,
                provider,
                self.__branch_used,
            )
            return

        details = "\n".join(f"{name}: {cause}" for name, cause in failures)
        error_msg = f"All providers failed to clone repository '{repository_name}':\n{details}"
        raise ProviderError(error_msg)

    def _provider_remote_exists(self, provider: ProviderBase, repository_name: str) -> bool:
        """Check whether a single provider reports the repository as existing.

        Args:
            provider: Provider instance to check.
            repository_name: Name of the repository to check.

        Returns:
            bool: True if the provider confirms the repository exists, False
            otherwise (including when the check itself raises).

        """
        try:
            return provider.remote_exists(repository_name)
        except Exception as e:
            # Log only exception type to avoid exposing sensitive information.
            log.exception(
                "Provider %s failed to check repository existence: %s",
                provider,
                type(e).__name__,
            )
            return False

    @override
    def remote_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists using the first available provider.

        Args:
            repository_name: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        return any(self._provider_remote_exists(provider, repository_name) for provider in self.providers)

    @override
    def __str__(self) -> str:
        """Return string representation of the selector provider.

        Returns:
            String representation of the selector provider.

        """
        return f"SelectorProvider(providers={self.providers})"

    @override
    def __repr__(self) -> str:
        """Return detailed string representation of the selector provider.

        Returns:
            Detailed string representation of the selector provider.

        """
        return f"SelectorProvider(providers={self.providers})"

    @override
    def get_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Name of the provider.

        """
        return self.name

    @override
    def get_branch(self) -> str:
        """Get the branch of the provider.

        Returns:
            str: Branch of the provider.

        """
        return self.__branch_used or ""
