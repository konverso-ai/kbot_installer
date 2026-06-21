from typing import cast

from writer.base import Writer
from utils.factory.factory import factory_object


def create_writer(name: str, **kwargs: object) -> Writer:
    """Create a writer instance."""
    return cast(Writer, factory_object(name, "writer", **kwargs))
