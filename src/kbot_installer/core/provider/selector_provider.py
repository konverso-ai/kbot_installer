"""Selector provider for automatic provider selection.

This module implements the SelectorProvider class that automatically selects
the appropriate provider based on repository availability. It tries multiple
providers in sequence until it finds one that has the repository.
"""

import asyncio
import inspect
import logging
import re
from pathlib import Path

from kbot_installer.core.provider.config import (
    DEFAULT_PROVIDERS_CONFIG,
    ProvidersConfig,
)
from kbot_installer.core.provider.credential_manager import CredentialManager
from kbot_installer.core.provider.factory import create_provider
from kbot_installer.core.provider.provider_base import ProviderBase, ProviderError


def _run_coroutine_safe(coro: object) -> object:
    """Run a coroutine safely from a sync context.

    Args:
        coro: The coroutine to run.

    Returns:
        The result of the coroutine execution.

    """
    # Try to use asyncio.run() first (preferred method)
    try:
        # Check if there's already a running event loop
        asyncio.get_running_loop()
        # If we get here, a loop is already running
        # Use a new event loop instead
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    except RuntimeError:
        # No running event loop - safe to use asyncio.run()
        return asyncio.run(coro)


logger = logging.getLogger(__name__)

# Constants
MAX_CAUSE_LENGTH = 50


class SelectorProvider(ProviderBase):
    """Provider that automatically selects the appropriate provider.

    This provider tries multiple providers in sequence to find and clone
    a repository. It will attempt each provider in the order specified
    until it finds one that has the repository.

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
    ) -> None:
        """Initialize the selector provider.

        Args:
            providers: List of provider names to try in order (e.g., ["nexus", "github", "bitbucket"]).
            base_url: Base URL (not used for selector, defaults to empty string).
            config: Configuration for all providers. Defaults to DEFAULT_PROVIDERS_CONFIG.

        """
        self.base_url = base_url
        self.providers = providers
        self.config = config
        self.credential_manager = CredentialManager(config)
        # Store the branch that was successfully used
        self.branch_used: str | None = None

    def _create_provider_with_credentials(
        self, provider_name: str
    ) -> ProviderBase | None:
        """Create a provider instance with credentials from environment variables.

        Args:
            provider_name: Name of the provider to create.

        Returns:
            ProviderBase | None: The created provider instance with credentials, or None if credentials are missing.

        """
        logger.info("Creating provider '%s' with credentials", provider_name)

        # Get provider configuration
        logger.info("Getting provider configuration for '%s'", provider_name)
        provider_config = self.config.get_provider_config(provider_name)
        if not provider_config:
            logger.warning("No configuration found for provider: %s", provider_name)
            return None

        logger.info(
            "Provider configuration found for '%s': %s", provider_name, provider_config
        )

        # For GitHub and Bitbucket, allow creation without credentials (for public repos)
        # For Nexus, credentials are required
        if provider_name not in [
            "github",
            "bitbucket",
        ] and not self.credential_manager.has_credentials(provider_name):
            logger.debug(
                "Credentials required for provider '%s' but not available",
                provider_name,
            )
            return None

        params = provider_config.kwargs.copy()

        # Add authentication if available
        auth = self.credential_manager.get_auth_for_provider(provider_name)
        logger.info("Authentication found for '%s': %s", provider_name, auth)
        if auth:
            params["auth"] = auth
            logger.info(
                "Authentication added to parameters for '%s': %s", provider_name, params
            )

        try:
            logger.info(
                "Creating provider '%s' with parameters: %s", provider_name, params
            )
            return create_provider(name=provider_name, **params)
        except ProviderError as e:
            logger.exception(
                "Failed to create provider '%s': %s", provider_name, type(e).__name__
            )
            return None
        except Exception as e:
            # Log error without exposing sensitive information from stack trace
            # Using logger.error() instead of logger.exception() to prevent
            # credential exposure in stack traces (security best practice)
            logger.error(  # noqa: TRY400
                "Failed to create provider '%s': %s",
                provider_name,
                type(e).__name__,
            )
            return None

    def clone_and_checkout(
        self,
        target_path: str | Path,
        branch: str | None = None,
        *,
        repository_url: str | None = None,
        repository_name: str | None = None,
    ) -> None:
        """Clone a repository using the first available provider and optionally checkout a branch.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.
            repository_url: URL of the repository to clone (mutually exclusive with repository_name).
            repository_name: Name of the repository to clone (mutually exclusive with repository_url).

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
            self._clone_by_url(repository_url, target_path, branch)
        else:
            self._clone_by_name(repository_name, target_path, branch)

    def _print_clone_results_table(self, results: list[tuple[str, str, str]]) -> None:
        """Print a formatted table showing clone results for each provider.

        Args:
            results: List of tuples (provider_name, status, cause).

        """
        if not results:
            return

        # Headers

        # Results
        for _provider, _status, cause in results:
            # Truncate long causes
            cause[:MAX_CAUSE_LENGTH] + "..." if len(cause) > MAX_CAUSE_LENGTH else cause

    def _extract_clean_error_cause(self, error_message: str) -> str:
        """Extract a clean, readable error cause from error messages.

        Args:
            error_message: The full error message.

        Returns:
            str: A clean, readable error cause.

        """
        # Check for HTTP status codes
        http_error = self._extract_http_error(error_message)
        if http_error:
            return http_error

        # Check for connection issues
        if self._is_connection_error(error_message):
            return "Connection failed"

        # Check for timeout
        if "timeout" in error_message.lower():
            return "Request timeout"

        # Check for streaming download errors
        if "Streaming download/extraction failed" in error_message:
            return self._extract_streaming_error(error_message)

        # For other errors, take the last meaningful part
        return self._extract_last_meaningful_part(error_message)

    def _extract_http_error(self, error_message: str) -> str | None:
        """Extract HTTP error information from error message."""
        if "404 Not Found" in error_message:
            return "Repository not found (404)"
        if "401 Unauthorized" in error_message:
            return "Authentication failed (401)"
        if "403 Forbidden" in error_message:
            return "Access forbidden (403)"
        if "500 Internal Server Error" in error_message:
            return "Server error (500)"
        return None

    def _is_connection_error(self, error_message: str) -> bool:
        """Check if error is related to connection issues."""
        return "Connection" in error_message and "failed" in error_message

    def _extract_streaming_error(self, error_message: str) -> str:
        """Extract error from streaming download failures."""
        if "Client error" in error_message:
            match = re.search(r"Client error '(\d+ [^']+)'", error_message)
            if match:
                return f"HTTP {match.group(1)}"
        return "Download failed"

    def _extract_last_meaningful_part(self, error_message: str) -> str:
        """Extract the last meaningful part of an error message."""
        # For version not found errors, preserve the full message
        if "Version" in error_message and "not found" in error_message:
            return error_message

        # For repository not found errors, preserve the full message
        if "Repository" in error_message and "not found" in error_message:
            return error_message

        # For authentication errors, preserve the full message
        if "Authentication failed" in error_message or "auth" in error_message.lower():
            return error_message

        # For other errors, take the last meaningful part
        parts = error_message.split(":")
        if len(parts) > 1:
            return parts[-1].strip()
        return error_message

    def __str__(self) -> str:
        """Return string representation of the selector provider.

        Returns:
            String representation of the selector provider.

        """
        return f"SelectorProvider(providers={self.providers})"

    def _get_branches_to_try(self, provider_name: str, branch: str | None) -> list[str]:
        """Get list of branches to try for a provider.

        Args:
            provider_name: Name of the provider.
            branch: Requested branch, or None for default.

        Returns:
            List of branches to try in order.

        """
        # Handle both ProvidersConfig objects and dict configs (for testing)
        if hasattr(self.config, "get_provider_config"):
            provider_config = self.config.get_provider_config(provider_name)
        elif isinstance(self.config, dict):
            # For dict configs (used in tests), just return the requested branch
            return [branch] if branch else []
        else:
            return [branch] if branch else []

        if not provider_config:
            return [branch] if branch else []

        # Check if provider_config has branches attribute (it should be a ProviderConfig)
        if not hasattr(provider_config, "branches"):
            return [branch] if branch else []

        if branch:
            # Try requested branch first, then fallbacks
            return [branch, *provider_config.branches]

        # No branch specified, use first fallback as default
        return [provider_config.branches[0]] if provider_config.branches else []

    def _try_clone_with_branch(
        self,
        provider: ProviderBase,
        repository_name: str,
        target_path: Path,
        branch_to_try: str | None,
    ) -> None:
        """Attempt to clone with a specific branch.

        Args:
            provider: Provider instance to use.
            repository_name: Name or URL of repository.
            target_path: Local path where repository should be cloned.
            branch_to_try: Branch to try, or None for default.

        Raises:
            ProviderError: If clone fails.

        """
        # Check if the method itself is async before calling it
        clone_method = provider.clone_and_checkout
        is_async_method = inspect.iscoroutinefunction(clone_method)

        logger.debug(
            "clone_and_checkout is async: %s for provider %s",
            is_async_method,
            type(provider).__name__,
        )

        try:
            if is_async_method:
                # Method is async, call it and await the result
                logger.debug("Calling async clone_and_checkout")
                result = clone_method(repository_name, target_path, branch_to_try)
                logger.debug("Got coroutine result, running with asyncio")
                # Run the coroutine
                _run_coroutine_safe(result)
                logger.debug("Async clone completed")
            else:
                # Method is sync, call it directly
                logger.debug("Calling sync clone_and_checkout")
                clone_method(repository_name, target_path, branch_to_try)
                logger.debug("Sync clone completed")
        except ProviderError:
            # Re-raise ProviderError as-is
            raise
        except Exception as e:
            # Wrap other exceptions in ProviderError, preserving the original exception info
            error_msg = f"Unexpected error during clone: {type(e).__name__}: {e}"
            raise ProviderError(error_msg) from e

    def _is_branch_not_found_error(self, error: ProviderError) -> bool:
        """Check if error indicates branch/version not found.

        Args:
            error: ProviderError to check.

        Returns:
            True if error indicates branch not found.

        """
        error_str = str(error).lower()
        return (
            "not found" in error_str or "branch" in error_str or "version" in error_str
        )

    def _update_provider_name(self, provider: ProviderBase) -> None:
        """Update provider name if get_name is available.

        Args:
            provider: Provider instance to get name from.

        """
        try:
            if hasattr(provider, "get_name") and callable(
                getattr(provider, "get_name", None)
            ):
                self.name = provider.get_name()
        except Exception as e:
            # Log but ignore errors when getting provider name
            logger.debug("Failed to get provider name: %s", type(e).__name__)

    def _build_success_message(
        self, branch_to_try: str, requested_branch: str | None
    ) -> str:
        """Build success message for successful clone.

        Args:
            branch_to_try: Branch that was successfully used.
            requested_branch: Originally requested branch.

        Returns:
            Success message string.

        """
        if not requested_branch:
            return f"Repository cloned successfully (default branch: '{branch_to_try}')"
        if branch_to_try == requested_branch:
            return f"Repository cloned successfully with branch '{branch_to_try}'"
        return (
            f"Repository cloned successfully with fallback branch '{branch_to_try}' "
            f"(requested branch '{requested_branch}' not found)"
        )

    def _handle_clone_error(
        self, error: ProviderError, branch_to_try: str, branches_to_try: list[str]
    ) -> bool:
        """Handle clone error, determine if should try next branch.

        Args:
            error: The ProviderError that occurred.
            branch_to_try: Current branch being tried.
            branches_to_try: List of all branches to try.

        Returns:
            True if should continue with next branch, False if should raise.

        """
        if (
            self._is_branch_not_found_error(error)
            and branch_to_try != branches_to_try[-1]
        ):
            logger.debug("Branch '%s' not found, trying fallback branch", branch_to_try)
            return True
        return False

    def _clone_with_provider_and_branches(
        self,
        provider: ProviderBase,
        provider_name: str,
        repository_name: str,
        target_path: Path,
        requested_branch: str | None,
    ) -> tuple[str, str]:
        """Clone repository with a provider, trying branches in fallback order.

        Args:
            provider: Provider instance to use.
            provider_name: Name of the provider (for logging).
            repository_name: Name or URL of repository.
            target_path: Local path where repository should be cloned.
            requested_branch: Requested branch, or None for default.

        Returns:
            Tuple of (branch_used, success_message).

        Raises:
            ProviderError: If all branches fail.

        """
        branches_to_try = self._get_branches_to_try(provider_name, requested_branch)

        last_error = None
        for branch_to_try in branches_to_try:
            try:
                self._try_clone_with_branch(
                    provider, repository_name, target_path, branch_to_try
                )
                self._update_provider_name(provider)

            except ProviderError as e:
                last_error = e
                if self._handle_clone_error(e, branch_to_try, branches_to_try):
                    continue
                raise
            else:
                msg = self._build_success_message(branch_to_try, requested_branch)
                return branch_to_try, msg

        # All branches failed
        if last_error:
            raise last_error
        error_msg = (
            f"Failed to clone with any branch from fallback list: {branches_to_try}"
        )
        raise ProviderError(error_msg)

    def _handle_provider_failure(
        self, provider_name: str, error: Exception, results: list[tuple[str, str, str]]
    ) -> None:
        """Handle provider failure and add to results.

        Args:
            provider_name: Name of the provider that failed.
            error: Exception that occurred.
            results: List to append failure result to.

        """
        if isinstance(error, ProviderError):
            cause = self._extract_clean_error_cause(str(error))
            logger.debug(
                "Provider '%s' failed with ProviderError: %s",
                provider_name,
                type(error).__name__,
            )
        else:
            cause = f"Unexpected error: {type(error).__name__}"
            logger.debug(
                "Provider '%s' failed with unexpected error: %s",
                provider_name,
                type(error).__name__,
            )

        results.append((provider_name, "❌ FAILED", cause))

    def _clone_with_providers(
        self, repository_name: str, target_path: str | Path, branch: str | None = None
    ) -> None:
        """Clone a repository using available providers.

        Args:
            repository_name: Name or URL of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to clone. If None, clones the default branch.

        Raises:
            ProviderError: If all providers fail to clone the repository.

        """
        target_path = Path(target_path)
        target_path.mkdir(parents=True, exist_ok=True)

        results = []
        for provider_name in self.providers:
            logger.info(
                "Attempting to clone repository '%s' with provider: %s",
                repository_name,
                provider_name,
            )

            try:
                provider = self._create_provider_with_credentials(provider_name)
                if provider is None:
                    missing_creds = (
                        self.credential_manager.get_missing_credentials_info(
                            provider_name
                        )
                    )
                    cause = (
                        f"Missing credentials: {', '.join(missing_creds)}"
                        if missing_creds
                        else "Provider not available"
                    )
                    results.append((provider_name, "❌ FAILED", cause))
                    logger.debug(
                        "Provider '%s' not available (missing credentials or provider doesn't exist)",
                        provider_name,
                    )
                    continue

                branch_used, success_msg = self._clone_with_provider_and_branches(
                    provider, provider_name, repository_name, target_path, branch
                )
                # Store the branch that was successfully used
                self.branch_used = branch_used
                results.append((provider_name, "✅ SUCCESS", success_msg))
                logger.info(
                    "✅ Successfully cloned repository '%s' using provider: %s (branch: %s)",
                    repository_name,
                    provider_name,
                    branch_used,
                )

            except ProviderError as e:
                self._handle_provider_failure(provider_name, e, results)
                continue
            except Exception as e:
                self._handle_provider_failure(provider_name, e, results)
                continue

            return

        # All providers failed
        self._print_clone_results_table(results)
        failed_providers = [r for r in results if r[1] == "❌ FAILED"]
        if failed_providers:
            error_details = "\n".join(
                f"• {name}: {cause}" for name, _status, cause in failed_providers
            )
            error_msg = f"❌ All providers failed to clone repository '{repository_name}':\n{error_details}"
        else:
            error_msg = f"❌ No provider could clone repository '{repository_name}'"
        raise ProviderError(error_msg)

    def _clone_by_url(
        self, repository_name: str, target_path: str | Path, branch: str | None = None
    ) -> None:
        """Clone a repository by URL using the first available provider.

        Args:
            repository_name: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to clone. If None, clones the default branch.

        Raises:
            ProviderError: If all providers fail to clone the repository.

        """
        self._clone_with_providers(repository_name, target_path, branch)

    def _clone_by_name(
        self, repository_name: str, target_path: str | Path, branch: str | None = None
    ) -> None:
        """Clone a repository by name using the first available provider.

        This method tries each provider in order, and each provider will construct
        the appropriate URL based on its configuration.

        Args:
            repository_name: Name of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to clone. If None, clones the default branch.

        Raises:
            ProviderError: If all providers fail to clone the repository.

        """
        self._clone_with_providers(repository_name, target_path, branch)

    def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using the first available provider.

        Args:
            repository_url: URL or name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        for provider_name in self.providers:
            try:
                logger.info(
                    "Checking repository existence with provider: %s", provider_name
                )
                provider = self._create_provider_with_credentials(provider_name)
                if not provider:
                    continue

                exists = provider.check_remote_repository_exists(repository_url)

                logger.info(
                    "Repository exists with provider: %s: %s", provider_name, exists
                )

                if exists:
                    logger.info("Repository found with provider: %s", provider_name)
                    return True

            except Exception as e:
                # Log only exception type to avoid exposing sensitive information
                logger.exception(
                    "Provider %s failed to check repository existence: %s",
                    provider_name,
                    type(e).__name__,
                )

        logger.info("Repository not found with any provider")
        return False

    def __repr__(self) -> str:
        """Return detailed string representation of the selector provider.

        Returns:
            Detailed string representation of the selector provider.

        """
        return (
            f"SelectorProvider(providers={self.providers}, base_url='{self.base_url}')"
        )

    def get_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Name of the provider.

        """
        return self.name

    def get_branch(self) -> str:
        """Get the branch of the provider.

        Returns:
            str: Branch of the provider.

        """
        return self.branch_used or ""
