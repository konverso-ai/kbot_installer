"""Build the git authentication object matching a remote URL.

The transport is read from the remote URL itself (see
:mod:`git.remote_url`), so an SSH remote gets an :class:`~auth.ssh.ssh_auth.SshAuth`
and an HTTPS remote gets an :class:`~auth.http.basic_auth.BasicAuth`, without any
caller-side guessing.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

from auth.http.factory import add_http_auth
from auth.ssh.factory import add_ssh_auth
from auth.ssh.ssh_auth import DEFAULT_KEY_FILENAMES
from git.remote_url import RemoteScheme, detect_remote_scheme

if TYPE_CHECKING:
    from git.auth_protocol import GitAuthProtocol

__all__ = ["add_auth_for_scheme", "add_auth_for_url"]

_DEFAULT_SSH_DIRECTORY = Path.home() / ".ssh"


def add_auth_for_url(
    url: str,
    *,
    username: str | None = None,
    password: str | None = None,
    **ssh_kwargs: object,
) -> "GitAuthProtocol | None":
    """Create the authentication object required by a remote URL.

    Args:
        url: Remote URL or local path of the repository.
        username: HTTP username, required for HTTPS remotes.
        password: HTTP password or token, required for HTTPS remotes.
        **ssh_kwargs: Extra arguments forwarded to ``SshAuth`` for SSH remotes
            (``private_key``, ``use_agent``, ``ssh_directory``, ...).

    Returns:
        The authentication object, or None when the transport needs none
        (local path, ``file://`` or anonymous ``git://``).

    Raises:
        ValueError: If the URL scheme is unsupported, or if credentials are
            missing for an HTTPS remote.

    """
    return add_auth_for_scheme(
        detect_remote_scheme(url),
        username=username,
        password=password,
        **ssh_kwargs,
    )


def add_auth_for_scheme(
    scheme: RemoteScheme,
    *,
    username: str | None = None,
    password: str | None = None,
    **ssh_kwargs: object,
) -> "GitAuthProtocol | None":
    """Create the authentication object required by a transport.

    Args:
        scheme: Transport detected from the remote URL.
        username: HTTP username, required for HTTPS remotes.
        password: HTTP password or token, required for HTTPS remotes.
        **ssh_kwargs: Extra arguments forwarded to ``SshAuth`` for SSH remotes.

    Returns:
        The authentication object, or None when the transport needs none.

    Raises:
        ValueError: If credentials are missing for an HTTPS remote.

    """
    if not scheme.needs_auth:
        return None

    if scheme is RemoteScheme.SSH:
        return cast("GitAuthProtocol", add_ssh_auth("ssh", **_ssh_options(ssh_kwargs)))

    if not username or not password:
        msg = "An HTTP(S) git remote requires both a username and a password"
        raise ValueError(msg)

    return cast(
        "GitAuthProtocol",
        add_http_auth("basic", username=username, password=password),
    )


def _ssh_options(ssh_kwargs: dict[str, object]) -> dict[str, object]:
    """Complete SSH options with an agent fallback when no key file exists.

    ``git`` itself falls back to the agent when ``~/.ssh`` holds no usable key,
    so an explicit ``SSH_AUTH_SOCK`` is honoured rather than failing on a
    missing key file. An explicit ``use_agent`` or ``private_key`` always wins.
    """
    options = dict(ssh_kwargs)
    if "use_agent" in options or "private_key" in options:
        return options

    if not os.environ.get("SSH_AUTH_SOCK"):
        return options

    directory = options.get("ssh_directory")
    ssh_directory = Path(cast("str | Path", directory)) if directory else _DEFAULT_SSH_DIRECTORY
    if not any((ssh_directory / name).is_file() for name in DEFAULT_KEY_FILENAMES):
        options["use_agent"] = True

    return options
