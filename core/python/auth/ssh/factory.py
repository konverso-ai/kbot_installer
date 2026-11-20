"""Factory functions for authentication classes."""

from typing import cast

from auth.ssh.base import SshAuthBase
from utils.factory.loader import factory_function
from utils.factory.utils import build_class_name, build_module_name


def add_ssh_auth(name: str, **kwargs: object) -> SshAuthBase:
    """Create an authentication instance by name.

    Naming convention:
    - Module: ``auth.ssh.{name}_auth`` (e.g. ``auth.ssh.ssh_auth``)
    - Class: ``{Name}Auth`` (e.g. ``SshAuth``)

    Args:
        name: Base name of the authentication type (e.g. ``"basic"``, ``"bearer"``).
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the specified authentication class.

    """
    module_name = build_module_name(name, "auth")
    class_name = build_class_name(name, "auth")
    cls = factory_function(f"auth.ssh.{module_name}", class_name)
    return cast("SshAuthBase", cls(**kwargs))
