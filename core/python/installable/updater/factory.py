"""Factory functions for WorkareaInstallable updater instances."""

from enum import Enum
from typing import cast

from installable.updater.base import UpdaterBase
from utils.factory.factory import factory_method


class UpdaterName(str, Enum):
    STRICT = "strict"
    SMOOTH = "smooth"
    REPAIR = "repair"
    INTERACTIVE = "interactive"


def add_updater(name: str, **kwargs: object) -> UpdaterBase:
    """Create an updater instance by name.

    Naming convention:
    - Module: ``{name}_updater`` (e.g. ``strict_updater``)
    - Class: ``{Name}Updater`` (e.g. ``StrictUpdater``)

    Args:
        name: Base name of the updater type (e.g. ``"strict"``, ``"smooth"``).
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the specified updater class.

    """
    return cast(UpdaterBase, factory_method(name, "installable.updater", **kwargs))
