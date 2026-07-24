"""Credential manager for handling authentication via environment variables.

This module provides a CredentialManager class that manages authentication
credentials for different providers using environment variables. It provides
a clean interface to check credential availability and create authentication
objects without hardcoding credentials in the code.
"""

from auth.base import HttpAuthBase
from auth.factory import create_auth
from git.provider.config import (
    DEFAULT_PROVIDERS_CONFIG,
    ProviderConfig,
    ProvidersConfig,
)
from utils.Logger import logger

log = logger.get_package_logger("git.provider")


class CredentialManager:
    """Manages authentication credentials via environment variables.

    This class provides methods to check credential availability and create
    authentication objects for different providers without hardcoding credentials
    in the code. It uses environment variables to determine credential validity.

    Attributes:
        config (ProvidersConfig): Configuration for all providers.

    """

    def __init__(self, config: ProvidersConfig = DEFAULT_PROVIDERS_CONFIG) -> None:
        """Initialize the credential manager.

        Args:
            config: Configuration for all providers. Defaults to DEFAULT_PROVIDERS_CONFIG.

        """
        self.config = config

    def has_credentials(self, provider_name: str) -> bool:
        """Check if credentials are available for a provider.

        Args:
            provider_name: Name of the provider to check credentials for.

        Returns:
            bool: True if all required credentials are available, False otherwise.

        """
        credentials = self.config.get_credentials(provider_name)
        if credentials is None:
            log.warning("Unknown provider: %s", provider_name)
            return False

        missing_vars = credentials.missing_env_vars()
        if missing_vars:
            log.debug(
                "Missing environment variables for %s: %s",
                provider_name,
                missing_vars,
            )
            return False

        log.debug("All is good for %s", provider_name)
        return True

    def _create_auth_object(
        self,
        provider_config: ProviderConfig,
        provider_name: str,
    ) -> HttpAuthBase | None:
        """Create authentication object based on configuration.

        Args:
            provider_config: Configuration for the provider.
            provider_name: Name of the provider.

        Returns:
            Authentication object if successful, None otherwise.

        """
        credentials = self.config.get_credentials(provider_name)
        if credentials is None:
            return None

        try:
            auth_kwargs = credentials.auth_kwargs()
            if not auth_kwargs:
                return None

            return create_auth(provider_config.auth_type, **auth_kwargs)

        except ImportError as e:
            log.error(  # noqa: TRY400
                "Failed to import authentication module for auth_type '%s': %s",
                provider_config.auth_type,
                type(e).__name__,
            )
            return None
        except Exception as e:
            log.error(  # noqa: TRY400
                "Failed to create authentication object for auth_type '%s': %s",
                provider_config.auth_type,
                type(e).__name__,
            )
            return None

    def get_auth_for_provider(self, provider_name: str) -> HttpAuthBase | None:
        """Get authentication object for a specific provider.

        Args:
            provider_name: Name of the provider to get authentication for.

        Returns:
            HttpAuthBase | None: Authentication object if available, None otherwise.

        """
        if not self.has_credentials(provider_name):
            return None

        provider_config = self.config.get_provider_config(provider_name)
        if not provider_config:
            log.warning("Unknown provider: %s", provider_name)
            return None

        return self._create_auth_object(provider_config, provider_name)

    def get_available_providers(self) -> list[str]:
        """Get list of providers with available credentials.

        Returns:
            list[str]: List of provider names that have valid credentials.

        """
        return [
            provider
            for provider in self.config.get_available_providers()
            if self.has_credentials(provider)
        ]

    def get_missing_credentials_info(self, provider_name: str) -> list[str]:
        """Get information about missing credentials for a provider.

        Args:
            provider_name: Name of the provider to check.

        Returns:
            list[str]: List of missing environment variable names.

        """
        credentials = self.config.get_credentials(provider_name)
        if credentials is None:
            return [f"Unknown provider: {provider_name}"]

        return credentials.missing_env_vars()
