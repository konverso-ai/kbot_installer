"""Configuration structures for providers."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderConfig:
    """Configuration for a single provider.

    Attributes:
        kwargs: Default parameters for provider creation
        env_vars: Required environment variables
        auth_type: Type of authentication (http_auth, pygit_auth)
        auth_params: Mapping of auth parameters to environment variables
        branches: List of default branches to try in order

    """

    kwargs: dict[str, Any]
    env_vars: list[str]
    auth_type: str
    auth_params: dict[str, str]
    branches: list[str]


@dataclass
class ProvidersConfig:
    """Configuration for all providers.

    Attributes:
        providers: Dictionary mapping provider names to their configurations

    """

    providers: dict[str, ProviderConfig]

    def get_provider_config(self, provider_name: str) -> ProviderConfig | None:
        """Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider to get configuration for.

        Returns:
            ProviderConfig if found, None otherwise.

        """
        return self.providers.get(provider_name)

    def get_available_providers(self) -> list[str]:
        """Get list of configured provider names.

        Returns:
            List of provider names.

        """
        return list(self.providers.keys())


# Default configuration for all providers
DEFAULT_PROVIDERS_CONFIG = ProvidersConfig(
    providers={
        "nexus": ProviderConfig(
            kwargs={"domain": "nexus.konverso.ai", "repository": "kbot_raw"},
            env_vars=["NEXUS_USERNAME", "NEXUS_PASSWORD"],
            auth_type="http_auth",
            auth_params={"username": "NEXUS_USERNAME", "password": "NEXUS_PASSWORD"},
            branches=["master", "dev"],
        ),
        "github": ProviderConfig(
            kwargs={"account_name": "konverso-ai"},
            env_vars=["GITHUB_TOKEN"],
            auth_type="pygit_auth",
            auth_params={"username": "git", "password": "GITHUB_TOKEN"},
            branches=["main", "dev"],
        ),
        "bitbucket": ProviderConfig(
            kwargs={"account_name": "konversoai"},
            env_vars=["BITBUCKET_USERNAME", "BITBUCKET_APP_PASSWORD"],
            auth_type="pygit_auth",
            auth_params={
                "username": "BITBUCKET_USERNAME",
                "password": "BITBUCKET_APP_PASSWORD",
            },
            branches=["master", "dev"],
        ),
    }
)
