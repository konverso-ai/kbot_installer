"""Factory functions for installable instances."""

from typing import Literal, cast

from installable.base import InstallableBase
from utils.factory.factory import factory_class


def create_installable(
    installable_name: Literal["workarea"],
    **kwargs: object,
) -> InstallableBase:
    """Create an installable instance by name.

    Naming convention:
    - Module: ``{name}_installable`` (e.g. ``workarea_installable``)
    - Class: ``{Name}Installable`` (e.g. ``WorkareaInstallable``)

    Args:
        installable_name: Installable type. Only ``workarea`` is supported.
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the requested installable class.

    """
    cls = factory_class(installable_name, "installable")
    return cast("InstallableBase", cls(**kwargs))
