"""Factory functions for Workarea updatable instances."""

from enum import Enum
from typing import cast

from updatable.base import UpdatableBase
from utils.factory.loader import factory_method


class UpdatableName(str, Enum):
    """Names of the available Workarea updatable strategies."""

    STRICT = "strict"
    SMOOTH = "smooth"
    REPAIR = "repair"
    INTERACTIVE = "interactive"


def add_updatable(name: str, **kwargs: object) -> UpdatableBase:
    """Create an updatable instance by name.

    Naming convention:
    - Module: ``{name}_updatable`` (e.g. ``strict_updatable``)
    - Class: ``{Name}Updatable`` (e.g. ``StrictUpdatable``)

    Args:
        name: Base name of the updatable type (e.g. ``"strict"``, ``"smooth"``).
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the specified updatable class.

    """
    return cast("UpdatableBase", factory_method(name, "updatable", **kwargs))
