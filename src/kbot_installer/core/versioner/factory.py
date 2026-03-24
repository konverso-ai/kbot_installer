"""Factory functions for creating versioner instances."""

from kbot_installer.core.factory.factory import factory_method
from kbot_installer.core.versioner.versioner_base import VersionerBase


def create_versioner(name: str, **kwargs: object) -> VersionerBase:
    """Create a versioner instance by name.

    Args:
        name: Name of the versioner to create (e.g., "pygit").
        **kwargs: Additional arguments to pass to the versioner constructor.

    Returns:
        An instance of the specified versioner.

    Raises:
        ImportError: If the versioner cannot be imported.
        AttributeError: If the versioner class is not found.
        TypeError: If the versioner cannot be instantiated with the provided arguments.

    Example:
        >>> versioner = create_versioner("pygit", auth=your_auth)
        >>> print(versioner)
        PyGitVersioner()

    """
    return factory_method(name, __package__, **kwargs)
