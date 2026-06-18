"""Factory functions for creating backend instances."""

from typing import cast

from backend.base import BackendBase
from utils.factory.factory import factory_method


def create_backend(name: str, **kwargs: object) -> BackendBase:
    """Create a backend instance by name.

    Args:
        name: Name of the backend to create (e.g., "s3").
        **kwargs: Additional arguments to pass to the backend constructor.

    Returns:
        An instance of the specified backend.

    """
    return cast(BackendBase, factory_method(name, "backend", **kwargs))
