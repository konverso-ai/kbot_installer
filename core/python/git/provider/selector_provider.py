"""Selector provider for automatic provider selection.

This module implements the SelectorProvider class that automatically selects
the appropriate provider based on repository availability. It tries multiple
providers in sequence until it finds one that has the repository, delegating
provider construction to :mod:`git.provider.provider_builder` and per-provider
branch fallback to :mod:`git.provider.branch_resolver`.
"""

from pathlib import Path

from typing_extensions import override

from git.provider.base import ProviderBase
from git.provider.branch_resolver import clone_with_branch_fallback, get_branches_to_try
from git.provider.config import (
    DEFAULT_PROVIDERS_CONFIG,
    ProvidersConfig,
)
from git.provider.credential_manager import CredentialManager
from git.provider.errors import ProviderError
from git.provider.provider_builder import build_provider
from installer_support.env_loader import format_missing_env_vars_message
from utils.Logger import logger

log = logger.get_package_logger("git.provider")


class SelectorProvider(ProviderBase):
    """Provider that automatically selects the appropriate provider.

    This provider tries each configured provider in order. The first one
    that succeeds wins; if all fail, a single ``ProviderError`` is raised
    listing every provider's failure reason.

    Attributes:
        base_url (str): Base URL (not used for selector).
        providers (list[str]): List of provider names to try in order.

    """

    name = ""

    def __init__(
        self,
        providers: list[str],
        base_url: str = "",
        config: ProvidersConfig = DEFAULT_PROVIDERS_CONFIG,
        *,
        quiet: bool = False,
    ) -> None:
        """Initialize the selector provider.

        Args:
            providers: List of provider names to try in order (e.g., ["storage", "github", "bitbucket"]).
            base_url: Base URL (not used for selector, defaults to empty string).
            config: Configuration for all providers. Defaults to DEFAULT_PROVIDERS_CONFIG.
            quiet: When True, suppress informational clone output.

        """
        self.base_url = base_url
        self.providers = providers
        self.config = config
        self.quiet = quiet
        self.credential_manager = CredentialManager(config)
        # Branch used by the provider that last succeeded.
        self.branch_used: str | None = None

    def _create_provider_with_credentials(
        self, provider_name: str
    ) -> ProviderBase | None:
        """Build a provider instance with credentials from the environment.

        Args:
            provider_name: Name of the provider to create.

        Returns:
            The built provider, or None if it is not configured or is
            missing required credentials.

        See Also:
            :func:`git.provider.provider_builder.build_provider`

        """
        return build_provider(
            provider_name, self.config, self.credential_manager, quiet=self.quiet
        )

    def _get_branches_to_try(
        self, provider_name: str, branch: str | None
    ) -> list[str]:
        """Get the ordered list of branches to try for a provider.

        See Also:
            :func:`git.provider.branch_resolver.get_branches_to_try`

        """
        return get_branches_to_try(self.config, provider_name, branch)

    def _update_provider_name(self, provider: ProviderBase) -> None:
        """Record the name reported by the provider that just succeeded.

        Args:
            provider: Provider instance to get the name from.

        """
        try:
            if hasattr(provider, "get_name") and callable(
                getattr(provider, "get_name", None)
            ):
                self.name = provider.get_name()
        except Exception as e:
            # Log but ignore errors when getting provider name.
            log.debug("Failed to get provider name: %s", type(e).__name__)

    @override
    def clone_and_checkout(
        self,
        target_path: str | Path,
        branch: str | None = None,
        *,
        repository_url: str | None = None,
        repository_name: str | None = None,
        commit: str | None = None,
    ) -> None:
        """Clone a repository using the first available provider.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.
            repository_url: URL of the repository to clone (mutually exclusive with repository_name).
            repository_name: Name of the repository to clone (mutually exclusive with repository_url).
            commit: Specific commit to pin the checkout to. Only honored by providers
                that support commit pinning (e.g. storage-backed providers); ignored
                by plain git providers.

        Raises:
            ProviderError: If all providers fail to clone the repository.
            ValueError: If neither repository_url nor repository_name is provided, or both are provided.

        """
        if repository_url and repository_name:
            msg = "Cannot specify both repository_url and repository_name"
            raise ValueError(msg)
        if not repository_url and not repository_name:
            msg = "Must specify either repository_url or repository_name"
            raise ValueError(msg)

        if repository_url:
            self._clone_by_url(repository_url, target_path, branch, commit=commit)
        elif repository_name:
            self._clone_by_name(repository_name, target_path, branch, commit=commit)

    def _clone_by_url(
        self,
        repository_url: str,
        target_path: str | Path,
        branch: str | None = None,
        *,
        commit: str | None = None,
    ) -> None:
        """Clone a repository by URL using the first available provider.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to clone. If None, clones the default branch.
            commit: Specific commit to pin the checkout to, when supported.

        Raises:
            ProviderError: If all providers fail to clone the repository.

        """
        self._clone_with_providers(
            repository_url, target_path, branch, by_url=True, commit=commit
        )

    def _clone_by_name(
        self,
        repository_name: str,
        target_path: str | Path,
        branch: str | None = None,
        *,
        commit: str | None = None,
    ) -> None:
        """Clone a repository by name using the first available provider.

        Args:
            repository_name: Name of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to clone. If None, clones the default branch.
            commit: Specific commit to pin the checkout to, when supported.

        Raises:
            ProviderError: If all providers fail to clone the repository.

        """
        self._clone_with_providers(
            repository_name, target_path, branch, by_url=False, commit=commit
        )

    def _clone_with_providers(
        self,
        repository_identifier: str,
        target_path: str | Path,
        branch: str | None = None,
        *,
        by_url: bool,
        commit: str | None = None,
    ) -> None:
        """Try each configured provider in order until one clones successfully.

        Args:
            repository_identifier: Repository URL or name.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to clone. If None, clones the default branch.
            by_url: Whether ``repository_identifier`` is a repository URL.
            commit: Specific commit to pin the checkout to, when supported.

        Raises:
            ProviderError: If every provider fails to clone the repository;
                the error lists every provider's failure reason.

        """
        target_path = Path(target_path)
        target_path.mkdir(parents=True, exist_ok=True)

        failures: list[tuple[str, str]] = []
        for provider_name in self.providers:
            try:
                provider = self._create_provider_with_credentials(provider_name)
                if provider is None:
                    missing_creds = (
                        self.credential_manager.get_missing_credentials_info(
                            provider_name
                        )
                    )
                    cause = (
                        format_missing_env_vars_message(missing_creds)
                        if missing_creds
                        else "Provider not available"
                    )
                    failures.append((provider_name, cause))
                    continue

                branches = self._get_branches_to_try(provider_name, branch)
                self.branch_used = clone_with_branch_fallback(
                    provider,
                    repository_identifier,
                    target_path,
                    branches,
                    by_url=by_url,
                    commit=commit,
                )
            except ProviderError as e:
                failures.append((provider_name, str(e)))
                continue
            except Exception as e:
                failures.append(
                    (provider_name, f"Unexpected error: {type(e).__name__}: {e}")
                )
                continue

            self._update_provider_name(provider)
            log_fn = log.debug if self.quiet else log.info
            log_fn(
                "Successfully cloned repository '%s' using provider: %s (branch: %s)",
                repository_identifier,
                provider_name,
                self.branch_used,
            )
            return

        details = "\n".join(f"{name}: {cause}" for name, cause in failures)
        error_msg = (
            f"All providers failed to clone repository '{repository_identifier}':\n"
            f"{details}"
        )
        raise ProviderError(error_msg)

    @override
    def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using the first available provider.

        Args:
            repository_url: URL or name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        for provider_name in self.providers:
            try:
                provider = self._create_provider_with_credentials(provider_name)
                if not provider:
                    continue

                if provider.check_remote_repository_exists(repository_url):
                    return True

            except Exception as e:
                # Log only exception type to avoid exposing sensitive information.
                log.exception(
                    "Provider %s failed to check repository existence: %s",
                    provider_name,
                    type(e).__name__,
                )

        return False

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
        return (
            f"SelectorProvider(providers={self.providers}, base_url='{self.base_url}')"
        )

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
        return self.branch_used or ""
