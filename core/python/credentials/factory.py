"""Factory functions for credential instances."""

from typing import cast

from credentials.base import CredentialsBase
from utils.factory.factory import factory_method


def create_credentials(name: str, **kwargs: object) -> CredentialsBase:
    """Create a credentials instance by name.

    Naming convention:
    - Module: ``{name}_credentials`` (e.g. ``nexus_credentials``)
    - Class: ``{Name}Credentials`` (e.g. ``NexusCredentials``)

    Args:
        name: Base name of the credentials type (e.g. ``"nexus"``, ``"s3"``).
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the specified credentials class.

    """
    return cast(CredentialsBase, factory_method(name, "credentials", **kwargs))
