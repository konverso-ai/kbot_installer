"""Factory functions for creating bucket storage instances."""

from typing import cast

from storage.base import StorageBase
from utils.factory.factory import factory_method


def create_bucket_storage(name: str, **kwargs: object) -> StorageBase:
    """Create a bucket storage instance by name.

    Args:
        name: Name of the bucket storage to create (e.g., "s3").
        **kwargs: Additional arguments to pass to the bucket storage constructor.

    Returns:
        An instance of the specified bucket storage.

    """
    return cast(StorageBase, factory_method(name, "storage", **kwargs))
