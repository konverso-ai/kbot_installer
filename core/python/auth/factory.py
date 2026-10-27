"""Factory function dispatching authentication creation by transport."""

from typing import TYPE_CHECKING

from auth.http.factory import add_http_auth
from auth.ssh.factory import add_ssh_auth

if TYPE_CHECKING:
    from git.auth_protocol import GitAuthProtocol


def add_auth(auth_type: str, **kwargs: object) -> "GitAuthProtocol":
    """Create an authentication instance for the given transport.

    Dispatches ``"ssh"`` to :func:`add_ssh_auth` and any other transport
    (e.g. ``"basic"``) to :func:`add_http_auth`.

    Args:
        auth_type: Authentication transport, either ``"ssh"`` or an HTTP
            auth name understood by :func:`add_http_auth` (e.g. ``"basic"``).
        **kwargs: Keyword arguments passed to the underlying auth constructor.

    Returns:
        An instance of the matching authentication class.

    """
    if auth_type == "ssh":
        return add_ssh_auth("ssh", **kwargs)
    return add_http_auth(auth_type, **kwargs)
