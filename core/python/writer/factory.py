from typing import cast

from utils.factory.factory import factory_object
from writer.base import Writer


def add_writer(name: str, **kwargs: object) -> Writer:
    """Create a writer instance."""
    return cast("Writer", factory_object(name, "writer", **kwargs))
