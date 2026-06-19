"""Factory functions for creating versioner instances."""

from typing import cast

from utils.factory.factory import factory_method

from versioner.base import VersionerBase


def create_versioner(name: str, **kwargs: object) -> VersionerBase:
    """Create a versioner instance by name.

    Args:
        name: Name of the versioner to create (e.g., "dulwich").
        **kwargs: Additional arguments to pass to the versioner constructor.

    Returns:
        An instance of the specified versioner.

    Raises:
        ImportError: If the versioner cannot be imported.
        AttributeError: If the versioner class is not found.
        TypeError: If the versioner cannot be instantiated with the provided arguments.

    Example:
        >>> versioner = create_versioner("dulwich", auth=your_auth)
        >>> print(versioner)
        DulwichVersioner()

    """
    return cast(VersionerBase, factory_method(name, "versioner", **kwargs))
