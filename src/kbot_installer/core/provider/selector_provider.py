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

    def _create_provider_with_credentials(
        self, provider_name: str
    ) -> ProviderBase | None:
        """Create a provider instance with credentials from environment variables.

        Args:
            provider_name: Name of the provider to create.

        Returns:
            ProviderBase | None: The created provider instance with credentials, or None if credentials are missing.

        """
        # Check if credentials are available for this provider
        if not self.credential_manager.has_credentials(provider_name):
            logger.debug("No credentials available for provider: %s", provider_name)
            return None

        # Get provider configuration
        provider_config = self.config.get_provider_config(provider_name)
        if not provider_config:
            logger.warning("No configuration found for provider: %s", provider_name)
            return None

        params = provider_config.kwargs.copy()

        # Add authentication if available
        auth = self.credential_manager.get_auth_for_provider(provider_name)
        if auth:
            params["auth"] = auth

        try:
            return create_provider(name=provider_name, **params)
        except Exception:
            logger.exception("Failed to create provider '%s'", provider_name)
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

    def _clone_by_url(
        self, repository_name: str, target_path: str | Path, branch: str | None = None
    ) -> None:
        """Clone a repository by URL using the first available provider.

        Args:
            repository_name: Name of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to clone. If None, clones the default branch.

        Raises:
            ProviderError: If all providers fail to clone the repository.

        """
        target_path = Path(target_path)
        target_path.mkdir(parents=True, exist_ok=True)

        # Tableau pour afficher les résultats
        results = []
        success = False

        for provider_name in self.providers:
            logger.info("Attempting to clone with provider: %s", provider_name)

            try:
                # Try to create provider with credentials
                provider = self._create_provider_with_credentials(provider_name)

                if provider is None:
                    # Provider creation failed (no credentials or provider doesn't exist)
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

                # Try to clone the repository
                logger.debug("Attempting clone with provider '%s'", provider_name)

                # Handle both sync and async clone methods
                if inspect.iscoroutinefunction(provider.clone_and_checkout):
                    # Provider has async clone method
                    asyncio.run(
                        provider.clone_and_checkout(
                            repository_name, target_path, branch
                        )
                    )
                else:
                    # Provider has sync clone method
                    provider.clone_and_checkout(repository_name, target_path, branch)

                # Update the name of the provider
                self.name = provider.get_name()

                # Success! Log and mark as successful
                results.append(
                    (provider_name, "✅ SUCCESS", "Repository cloned successfully")
                )
                logger.info(
                    "✅ Successfully cloned repository using provider: %s",
                    provider_name,
                )
                success = True
                break
            except ProviderError as e:
                # Provider-specific error (e.g., repository not found, authentication failed)
                cause = self._extract_clean_error_cause(str(e))
                results.append((provider_name, "❌ FAILED", cause))
                logger.debug(
                    "Provider '%s' failed with ProviderError: %s", provider_name, e
                )
                continue
            except Exception as e:
                # Unexpected error during provider creation or clone
                cause = f"Unexpected error: {e!s}"
                results.append((provider_name, "❌ FAILED", cause))
                logger.debug(
                    "Provider '%s' failed with unexpected error: %s", provider_name, e
                )
                continue

        # If successful, return early
        if success:
            return

        # If we get here, no provider was able to clone the repository
        # Afficher le tableau des résultats
        self._print_clone_results_table(results)

        # Create detailed error message with all provider failures
        failed_providers = [result for result in results if result[1] == "❌ FAILED"]
        if failed_providers:
            error_details = []
            for provider_name, _status, cause in failed_providers:
                error_details.append(f"• {provider_name}: {cause}")

            error_details_text = "\n".join(error_details)
            error_msg = f"❌ All providers failed to clone repository '{repository_name}':\n{error_details_text}"
        else:
            error_msg = f"❌ No provider could clone repository '{repository_name}'"

        raise ProviderError(error_msg)

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
        target_path = Path(target_path)
        target_path.mkdir(parents=True, exist_ok=True)

        provider_errors = []
        success = False

        for provider_name in self.providers:
            try:
                provider = self._create_provider_with_credentials(provider_name)
                if not provider:
                    error_msg = (
                        f"Provider '{provider_name}' skipped: no credentials available"
                    )
                    logger.info("⚠️  %s", error_msg)
                    provider_errors.append(f"• {provider_name}: {error_msg}")
                    continue

                logger.info(
                    "🔄 Trying provider '%s' for repository '%s'",
                    provider_name,
                    repository_name,
                )

                # Skip repository existence check for now (pygit2.remote_ls issue)
                logger.debug(
                    "Skipping repository existence check for provider '%s'",
                    provider_name,
                )

                # Handle both sync and async providers
                if hasattr(provider, "clone_and_checkout") and callable(
                    provider.clone_and_checkout
                ):
                    if inspect.iscoroutinefunction(provider.clone_and_checkout):
                        # Provider has async clone method
                        asyncio.run(
                            provider.clone_and_checkout(
                                repository_name, target_path, branch
                            )
                        )
                    else:
                        # Provider has sync clone method
                        provider.clone_and_checkout(
                            repository_name, target_path, branch
                        )
                # Update the name of the provider
                self.name = provider.get_name()

                logger.info(
                    "✅ Successfully cloned repository using provider '%s'",
                    provider_name,
                )
                success = True
                break
            except Exception as e:
                error_msg = f"Provider '{provider_name}' failed: {e}"
                logger.info("❌ %s", error_msg)
                provider_errors.append(f"• {provider_name}: {e}")

        if success:
            return

        if provider_errors:
            # Create a detailed error message with all provider failures
            error_details = "\n".join(provider_errors)
            msg = f"❌ All providers failed to clone repository '{repository_name}':\n{error_details}"
            logger.error(msg)
            raise ProviderError(msg)

        msg = f"❌ No providers available to clone repository '{repository_name}'"
        logger.error(msg)
        raise ProviderError(msg)

    async def check_remote_repository_exists(self, repository_url: str) -> bool:
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
                provider = self._create_provider(provider_name)

                # Check if provider supports async check
                if inspect.iscoroutinefunction(provider.check_remote_repository_exists):
                    exists = await provider.check_remote_repository_exists(
                        repository_url
                    )
                else:
                    exists = provider.check_remote_repository_exists(repository_url)

                if exists:
                    logger.info("Repository found with provider: %s", provider_name)
                    return True

            except Exception as e:
                logger.warning(
                    "Provider %s failed to check repository existence: %s",
                    provider_name,
                    str(e),
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
