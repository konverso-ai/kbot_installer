"""Factory functions for credential instances."""

from typing import cast

from credentials.base import CredentialsBase
from utils.factory.loader import factory_function, factory_method
from utils.factory.utils import snake_to_pascal


def add_credentials(name: str, auth_type: str | None = None, **kwargs: object) -> CredentialsBase:
    """Create a credentials instance by name.

    Naming convention:
    - Module: ``{name}_credentials`` (e.g. ``nexus_credentials``)
    - Class: ``{Name}Credentials`` (e.g. ``NexusCredentials``)

    When ``auth_type`` is given (e.g. providers with an ssh/basic split like
    ``github``/``bitbucket``), it is folded into the naming convention instead:
    - Module: ``{name}.{auth_type}_{name}_credentials`` (e.g. ``github.ssh_github_credentials``)
    - Class: ``{AuthType}{Name}Credentials`` (e.g. ``SshGithubCredentials``)

    Args:
        name: Base name of the credentials type (e.g. ``"nexus"``, ``"s3"``, ``"github"``).
        auth_type: Authentication transport variant (e.g. ``"ssh"``, ``"basic"``),
            for providers whose credentials are split by transport.
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the specified credentials class.

    """
    if auth_type is not None:
        base_name = f"{auth_type}_{name}_credentials"
        module_name = f"credentials.{name}.{base_name}"
        class_name = snake_to_pascal(base_name)
        return cast("CredentialsBase", factory_function(module_name, class_name)(**kwargs))

    return cast("CredentialsBase", factory_method(name, "credentials", **kwargs))
