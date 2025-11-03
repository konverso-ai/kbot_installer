"""Factory functions for creating provider instances."""

from kbot_installer.core.factory.factory import factory_method
from kbot_installer.core.provider.provider_base import ProviderBase


def create_provider(name: str, **kwargs: object) -> ProviderBase:
    """Create a provider instance by name.

    Args:
        name: Name of the provider to create (e.g., "nexus").
        **kwargs: Additional arguments to pass to the provider constructor.

    Returns:
        An instance of the specified provider.

    Raises:
        ImportError: If the provider cannot be imported.
        AttributeError: If the provider class is not found.
        TypeError: If the provider cannot be instantiated with the provided arguments.

    Example:
        >>> nexus = create_provider("nexus", base_url="https://nexus.example.com")
        >>> print(nexus)
        NexusProvider(https://nexus.example.com)

    """
    return factory_method(name, __package__, **kwargs)
