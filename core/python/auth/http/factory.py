"""Factory functions for authentication classes."""

from typing import cast

from auth.base import HttpAuthBase
from utils.factory.loader import factory_function
from utils.factory.utils import build_class_name, build_module_name


def add_http_auth(name: str, **kwargs: object) -> HttpAuthBase:
    """Create an authentication instance by name.

    Naming convention:
    - Module: ``auth.http.{name}_auth`` (e.g. ``auth.http.basic_auth``)
    - Class: ``{Name}Auth`` (e.g. ``BasicAuth``)

    Args:
        name: Base name of the authentication type (e.g. ``"basic"``, ``"bearer"``).
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the specified authentication class.

    """
    module_name = build_module_name(name, "auth")
    class_name = build_class_name(name, "auth")
    cls = factory_function(f"auth.http.{module_name}", class_name)
    return cast("HttpAuthBase", cls(**kwargs))
