"""Factory functions for creating provider instances."""

from typing import cast

from git.provider.base import ProviderBase
from utils.factory.factory import factory_method


def create_provider(name: str, **kwargs: object) -> ProviderBase:
    """Create a provider instance by name.

    Args:
        name: Name of the provider to create (e.g., "storage").
        **kwargs: Additional arguments to pass to the provider constructor.

    Returns:
        An instance of the specified provider.

    Raises:
        ImportError: If the provider cannot be imported.
        AttributeError: If the provider class is not found.
        TypeError: If the provider cannot be instantiated with the provided arguments.

    Example:
        >>> storage = create_provider("storage")
        >>> print(storage)
        StorageProvider()

    """
    return cast("ProviderBase", factory_method(name, "git.provider", **kwargs))
