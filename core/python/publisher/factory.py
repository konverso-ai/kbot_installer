"""Factory functions for creating publisher instances."""

from publisher.base import PublisherBase
from utils.factory.loader import factory_object


def create_publisher(name: str, **kwargs: object) -> PublisherBase:
    """Create a publisher instance."""
    return factory_object(name, "publisher", **kwargs)
