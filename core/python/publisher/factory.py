"""Factory functions for creating publisher instances."""

from typing import cast

from publisher.base import PublisherBase
from utils.factory.factory import factory_object

def create_publisher(name: str, **kwargs: object) -> PublisherBase:
    """Create a publisher instance."""
    return cast(PublisherBase, factory_object(name, "publisher", **kwargs))
