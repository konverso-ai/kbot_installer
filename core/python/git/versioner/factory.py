"""Factory functions for creating versioner instances."""
from pathlib import Path
from typing import TYPE_CHECKING, cast

from auth.http.factory import add_http_auth
from auth.ssh.factory import add_ssh_auth
from credentials import add_credentials
from git.auth_factory import add_auth_for_url
from git.remote_url import RemoteScheme, detect_remote_scheme
from git.versioner.author import Author
from git.versioner.base import VersionerBase
from git.versioner.errors import RemoteNotFoundError, VersionerError
from utils.factory import factory_function
from utils.factory.loader import factory_method

if TYPE_CHECKING:
    from collections.abc import Callable

    from credentials.base import AuthCredentialsBase

# Hosts of HTTP remotes mapped to the provider whose credentials authenticate them.
_HTTP_HOST_PROVIDERS = {"github.com": "github", "bitbucket.org": "bitbucket"}

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


def add_basic_dulwich_versioner(
    username: str,
    password: str,
    author: Author | None = None,
) -> VersionerBase:
    """Create a Dulwich versioner configured with HTTP basic authentication.

    Args:
        username: HTTP username.
        password: HTTP password or access token.
        author: Author identity used for commit metadata.

    Returns:
        A Dulwich versioner instance using basic auth.

    """
    auth = add_http_auth(name="basic", username=username, password=password)
    return _build_dulwich_versioner(auth, author)


def add_ssh_dulwich_versioner(
    author: Author | None = None,
    **ssh_kwargs: object,
) -> VersionerBase:
    """Create a Dulwich versioner configured with SSH authentication.

    Args:
        author: Author identity used for commit metadata.
        **ssh_kwargs: Extra arguments forwarded to ``SshAuth``
            (``private_key``, ``use_agent``, ``ssh_directory``, ...).

    Returns:
        A Dulwich versioner instance using SSH auth.

    """
    auth = add_ssh_auth(name="ssh", **ssh_kwargs)
    return _build_dulwich_versioner(auth, author)


def add_dulwich_versioner_for_url(
    url: str,
    *,
    username: str | None = None,
    password: str | None = None,
    author: Author | None = None,
    **ssh_kwargs: object,
) -> VersionerBase:
    """Create a Dulwich versioner authenticated for a given remote URL.

    The transport is derived from the URL itself: ``git@host:org/repo.git`` and
    ``ssh://`` remotes use SSH, ``https://`` remotes use HTTP basic auth, and
    local paths use no authentication at all.

    Args:
        url: Remote URL or local path of the repository.
        username: HTTP username, required for HTTPS remotes.
        password: HTTP password or token, required for HTTPS remotes.
        author: Author identity used for commit metadata.
        **ssh_kwargs: Extra arguments forwarded to ``SshAuth`` for SSH remotes.

    Returns:
        A Dulwich versioner configured for that remote.

    Raises:
        ValueError: If the URL scheme is unsupported, or credentials are
            missing for an HTTPS remote.

    """
    auth = add_auth_for_url(
        url, username=username, password=password, **ssh_kwargs
    )
    return _build_dulwich_versioner(auth, author)


def add_dulwich_versioner_for_repository(
    repository_path: str | Path,
    *,
    username: str | None = None,
    password: str | None = None,
    author: Author | None = None,
    **ssh_kwargs: object,
) -> VersionerBase:
    """Create a Dulwich versioner authenticated for an existing local clone.

    Reads the ``origin`` URL of the clone — a purely local operation needing no
    credentials — then builds the versioner matching that remote's transport.
    A repository without an ``origin`` remote yields an unauthenticated
    versioner, which is all local-only operations need.

    Args:
        repository_path: Path to the local repository.
        username: HTTP username, required for HTTPS remotes.
        password: HTTP password or token, required for HTTPS remotes.
        author: Author identity used for commit metadata.
        **ssh_kwargs: Extra arguments forwarded to ``SshAuth`` for SSH remotes.

    Returns:
        A Dulwich versioner configured for that clone's remote.

    Raises:
        RepositoryNotFoundError: If the path is not a usable git repository.

    """
    probe = add_versioner(name="dulwich")
    try:
        url = probe.remote_url(repository_path)
    except (RemoteNotFoundError, VersionerError):
        return _build_dulwich_versioner(None, author)

    return add_dulwich_versioner_for_url(
        url,
        username=username,
        password=password,
        author=author,
        **ssh_kwargs,
    )


def add_versioner_for_repository_remote(repository_path: str | Path) -> VersionerBase:
    """Create a Dulwich versioner authenticated from a clone's ``origin`` remote.

    Unlike :func:`add_dulwich_versioner_for_repository`, credentials are not
    supplied by the caller: SSH remotes use the ``~/.ssh`` keys/agent, local
    paths need no authentication, and HTTP remotes on GitHub/Bitbucket use the
    basic credentials of that provider from the environment. A clone without
    ``origin``, or an HTTP remote without matching credentials, yields an
    anonymous versioner (remote operations then fail with a clear error, or
    succeed on public repositories).

    Args:
        repository_path: Path to the local repository.

    Returns:
        A Dulwich versioner able to fetch/pull from the clone's remote.

    Raises:
        ValueError: If the remote URL uses an unsupported scheme.

    """
    probe = add_versioner(name="dulwich")
    try:
        url = probe.remote_url(repository_path)
    except (RemoteNotFoundError, VersionerError):
        return probe

    if detect_remote_scheme(url) is not RemoteScheme.HTTP:
        return add_dulwich_versioner_for_url(url)

    provider_name = next((name for host, name in _HTTP_HOST_PROVIDERS.items() if host in url), None)
    if provider_name is None:
        return probe
    credentials = cast("AuthCredentialsBase", add_credentials(provider_name, auth_type="basic"))
    kwargs = credentials.auth_kwargs()
    if not kwargs:
        return probe
    return add_dulwich_versioner_for_url(url, username=str(kwargs["username"]), password=str(kwargs["password"]))


def _build_dulwich_versioner(
    auth: object | None, author: Author | None
) -> VersionerBase:
    """Instantiate a Dulwich versioner, omitting the author when unset."""
    kwargs: dict[str, object] = {"auth": auth}
    if author is not None:
        kwargs["author"] = author
    return add_versioner(name="dulwich", **kwargs)


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
