"""Factory for URL manager implementations.

This module provides factory functions for creating URL manager instances
using the project's factory package.
"""

from factory.factory import factory_object
from url_manager.url_manager_base import URLManagerBase


def create_url_manager(manager_type: str, base_url: str) -> URLManagerBase:
    """Create a URL manager instance by type.

    Args:
        manager_type (str): Type of URL manager to create (e.g., "furl").
        base_url (str): Base URL for the manager.

    Returns:
        URLManagerBase: A URL manager instance.

    Raises:
        ImportError: If the manager type is not found.
        AttributeError: If the manager class is not found.
        TypeError: If the manager cannot be instantiated.

    Example:
        >>> manager = create_url_manager("furl", "https://api.example.com")
        >>> print(manager)
        FurlManager(https://api.example.com)

    """
    return factory_object(manager_type, __package__, base_url=base_url)
