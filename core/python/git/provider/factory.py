"""Factory functions for creating provider instances."""

from typing import TYPE_CHECKING, cast

from auth.http.factory import add_http_auth
from auth.ssh.factory import add_ssh_auth
from credentials.bitbucket.basic_bitbucket_credentials import (
    BasicBitbucketCredentials,
)
from credentials.bitbucket.ssh_bitbucket_credentials import SshBitbucketCredentials
from credentials.github.basic_github_credentials import BasicGithubCredentials
from credentials.github.ssh_github_credentials import SshGithubCredentials
from git.provider.base import ProviderBase
from utils.factory import factory_function
from utils.factory.loader import factory_method

if TYPE_CHECKING:
    from collections.abc import Callable


def add_provider(name: str, **kwargs: object) -> ProviderBase:
    """Create a provider instance by name.

    Args:
        name: Name of the provider to create (e.g., "storage").
        **kwargs: Additional arguments to pass to the provider constructor.

    Returns:
        An instance of the specified provider.

    Raises:
        ImportError: If the provider cannot be imported.
        AttributeError: If the provider class is not found.
        TypeError: If the provider cannot be instantiated with the provided arguments.

    Example:
        >>> storage = create_provider("storage")
        >>> print(storage)
        StorageProvider()

    """
    return cast("ProviderBase", factory_method(name, "git.provider", **kwargs))


def ssh_github_provider() -> ProviderBase:
    """Create a GitHub provider authenticated via SSH."""
    credentials = SshGithubCredentials()
    auth = add_ssh_auth(name="ssh", **credentials.auth_kwargs())
    return add_provider(name="github", auth=auth)


def ssh_bitbucket_provider() -> ProviderBase:
    """Create a Bitbucket provider authenticated via SSH."""
    credentials = SshBitbucketCredentials()
    auth = add_ssh_auth(name="ssh", **credentials.auth_kwargs())
    return add_provider(name="bitbucket", auth=auth)


def basic_github_provider() -> ProviderBase:
    """Create a GitHub provider authenticated via HTTP basic auth."""
    credentials = BasicGithubCredentials()
    auth = add_http_auth(name="basic", **credentials.auth_kwargs())
    return add_provider(name="github", auth=auth)


def basic_bitbucket_provider() -> ProviderBase:
    """Create a Bitbucket provider authenticated via HTTP basic auth."""
    credentials = BasicBitbucketCredentials()
    auth = add_http_auth(name="basic", **credentials.auth_kwargs())
    return add_provider(name="bitbucket", auth=auth)


def add_transport_provider(transport: str, provider: str) -> ProviderBase:
    """Create a provider instance for a given transport and provider name.

    Dispatches to the matching helper defined in this module using the
    naming convention ``{transport}_{provider}_provider`` (e.g.
    ``ssh_github_provider``, ``basic_bitbucket_provider``).

    Args:
        transport: Authentication transport to use (e.g. "ssh", "basic").
        provider: Name of the git provider (e.g. "github", "bitbucket").

    Returns:
        An instance of the provider, authenticated via the given transport.

    Raises:
        ImportError: If the current module cannot be imported.
        AttributeError: If no ``{transport}_{provider}_provider`` function exists.

    Example:
        >>> provider = add_transport_provider("ssh", "github")
        >>> print(provider)
        GithubProvider()

    """
    builder = cast(
        "Callable[[], ProviderBase]",
        factory_function(
            module_name=__name__,
            attribute_name=f"{transport}_{provider}_provider",
        ),
    )
    return builder()
