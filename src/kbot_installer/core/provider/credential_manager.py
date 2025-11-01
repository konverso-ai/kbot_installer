"""Credential manager for handling authentication via environment variables.

This module provides a CredentialManager class that manages authentication
credentials for different providers using environment variables. It provides
a clean interface to check credential availability and create authentication
objects without hardcoding credentials in the code.
"""

import logging
import os

from kbot_installer.core.auth.http_auth import create_http_auth
from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase
from kbot_installer.core.auth.pygit_authentication import (
    PyGitAuthenticationBase,
    create_pygit_authentication,
)
from kbot_installer.core.provider.config import (
    DEFAULT_PROVIDERS_CONFIG,
    ProviderConfig,
    ProvidersConfig,
)

logger = logging.getLogger(__name__)


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
        provider_config = self.config.get_provider_config(provider_name)
        if not provider_config:
            logger.warning("Unknown provider: %s", provider_name)
            return False

        missing_vars = [var for var in provider_config.env_vars if not os.getenv(var)]

        if missing_vars:
            logger.debug("Missing credentials for %s: %s", provider_name, missing_vars)
            return False

        logger.debug("All credentials available for %s", provider_name)
        return True

    def _create_auth_object(
        self, provider_config: ProviderConfig
    ) -> HttpAuthBase | PyGitAuthenticationBase | None:
        """Create authentication object based on configuration.

        Args:
            provider_config: Configuration for the provider.

        Returns:
            Authentication object if successful, None otherwise.

        """
        try:
            # Get environment variables and fixed values
            env_values = {}
            for param, value in provider_config.auth_params.items():
                # If value is a known environment variable, get it from env
                if value in provider_config.env_vars:
                    env_values[param] = os.getenv(value)
                else:
                    # Otherwise, use the value as-is (fixed value like "git")
                    env_values[param] = value

            # Create appropriate auth object
            if provider_config.auth_type == "http_auth":
                result = create_http_auth("basic", **env_values)
            elif provider_config.auth_type == "pygit_auth":
                result = create_pygit_authentication("user_pass", **env_values)
            else:
                logger.warning("Unknown auth type: %s", provider_config.auth_type)
                result = None

        except ImportError as e:
            # Log error without exposing sensitive information from stack trace
            # Using logger.error() instead of logger.exception() to prevent
            # credential exposure in stack traces (security best practice)
            # Note: Intentionally using logger.error() instead of logger.exception()
            # to avoid logging stack traces that may contain credential values
            logger.error(  # noqa: TRY400
                "Failed to import authentication module for auth_type '%s': %s",
                provider_config.auth_type,
                type(e).__name__,
            )
            return None
        except Exception as e:
            # Log error without exposing sensitive information from stack trace
            # Do not log exception details that might contain credential values
            # Using logger.error() instead of logger.exception() to prevent
            # credential exposure in stack traces (security best practice)
            # Note: Intentionally using logger.error() instead of logger.exception()
            # to avoid logging stack traces that may contain credential values
            logger.error(  # noqa: TRY400
                "Failed to create authentication object for auth_type '%s': %s",
                provider_config.auth_type,
                type(e).__name__,
            )
            return None

        return result

    def get_auth_for_provider(
        self, provider_name: str
    ) -> HttpAuthBase | PyGitAuthenticationBase | None:
        """Get authentication object for a specific provider.

        Args:
            provider_name: Name of the provider to get authentication for.

        Returns:
            HttpAuthBase | PyGitAuthenticationBase | None: Authentication object if available, None otherwise.

        """
        if not self.has_credentials(provider_name):
            return None

        provider_config = self.config.get_provider_config(provider_name)
        if not provider_config:
            logger.warning("Unknown provider: %s", provider_name)
            return None

        return self._create_auth_object(provider_config)

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
        provider_config = self.config.get_provider_config(provider_name)
        if not provider_config:
            return [f"Unknown provider: {provider_name}"]

        return [var for var in provider_config.env_vars if not os.getenv(var)]
