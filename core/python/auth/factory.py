"""Factory functions for authentication classes."""

from typing import cast

from utils.factory.factory import factory_method

from auth.base import HttpAuthBase


def create_auth(name: str, **kwargs: object) -> HttpAuthBase:
    """Create an authentication instance by name.

    Naming convention:
    - Module: ``{name}_auth`` (e.g. ``basic_auth``)
    - Class: ``{Name}Auth`` (e.g. ``BasicAuth``)

    Args:
        name: Base name of the authentication type (e.g. ``"basic"``, ``"bearer"``).
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the specified authentication class.

    """
    return cast(HttpAuthBase, factory_method(name, "auth", **kwargs))
