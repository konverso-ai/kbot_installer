"""Provider package for repository cloning.

This package provides a unified interface for cloning repositories
from different providers like Nexus, GitHub, and Bitbucket.
"""

from git.provider.base import ProviderBase
from git.provider.config import DEFAULT_PROVIDERS_CONFIG
from git.provider.factory import create_provider

__all__ = [
    "DEFAULT_PROVIDERS_CONFIG",
    "ProviderBase",
    "create_provider",
]
