"""Factory functions for creating versioner instances."""
from typing import TYPE_CHECKING, cast

from auth.http.factory import add_http_auth
from auth.ssh.factory import add_ssh_auth
from git.versioner.base import VersionerBase
from utils.factory import factory_function
from utils.factory.loader import factory_method

if TYPE_CHECKING:
    from collections.abc import Callable


def add_versioner(name: str, **kwargs: object) -> VersionerBase:
    """Create a versioner instance by name.

    Args:
        name: Name of the versioner to create (e.g., "dulwich").
        **kwargs: Additional arguments to pass to the versioner constructor.

    Returns:
        An instance of the specified versioner.

    Raises:
        ImportError: If the versioner cannot be imported.
        AttributeError: If the versioner class is not found.
        TypeError: If the versioner cannot be instantiated with the provided arguments.

    Example:
        >>> versioner = add_versioner("dulwich", auth=your_auth)
        >>> print(versioner)
        DulwichVersioner()

    """
    return cast("VersionerBase", factory_method(name, "git.versioner", **kwargs))


def add_basic_dulwich_versioner() -> VersionerBase:
    """Create a Dulwich versioner configured with HTTP basic authentication.

    Returns:
        A Dulwich versioner instance using basic auth.

    """
    auth = add_http_auth(name="basic")
    return add_versioner(name="dulwich", auth=auth)


def add_ssh_dulwich_versioner() -> VersionerBase:
    """Create a Dulwich versioner configured with SSH authentication.

    Returns:
        A Dulwich versioner instance using SSH auth.

    """
    auth = add_ssh_auth(name="ssh")
    return add_versioner(name="dulwich", auth=auth)


def add_transport_versioner(name: str, transport: str, **kwargs: object) -> VersionerBase:
    """Create a versioner instance for a given transport (e.g., basic, ssh).

    Args:
        name: Name of the versioner to create (e.g., "dulwich").
        transport: Name of the transport/auth mechanism (e.g., "basic", "ssh").
        **kwargs: Additional arguments to pass to the versioner builder.

    Returns:
        An instance of the specified versioner configured for the given transport.

    """
    builder = cast(
        "Callable[..., VersionerBase]",
        factory_function(
            module_name=__name__,
            attribute_name=f"add_{transport}_{name}_versioner",
        ),
    )
    return builder(**kwargs)
