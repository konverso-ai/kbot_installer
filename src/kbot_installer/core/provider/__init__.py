"""Provider package for repository cloning.

This package provides a unified interface for cloning repositories
from different providers like Nexus, GitHub, and Bitbucket.
"""

from kbot_installer.core.provider.config import (
    DEFAULT_PROVIDERS_CONFIG,
    ProviderConfig,
    ProvidersConfig,
)
from kbot_installer.core.provider.factory import create_provider
from kbot_installer.core.provider.git_mixin import GitMixin
from kbot_installer.core.provider.provider_base import ProviderBase, ProviderError

__all__ = [
    "DEFAULT_PROVIDERS_CONFIG",
    "GitMixin",
    "ProviderBase",
    "ProviderConfig",
    "ProviderError",
    "ProvidersConfig",
    "create_provider",
]
