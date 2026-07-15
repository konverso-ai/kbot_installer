"""Factory for creating DownloadableBase instances by name."""

from typing import cast

from downloadable.base import DownloadableBase
from utils.factory.factory import factory_method


def add_downloadable(name: str, **kwargs: object) -> DownloadableBase:
    """Create a downloadable instance by name.

    Args:
        name: Name of the downloadable to create (e.g. "product", "bundle").
        **kwargs: Additional arguments to pass to the downloadable constructor.

    Returns:
        An instance of the specified downloadable.

    """
    return cast(
        "DownloadableBase",
        factory_method(name=name, package="downloadable", **kwargs),
    )
