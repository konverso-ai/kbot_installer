"""Detection of the transport used by a git remote URL.

Authentication must be chosen from the remote URL itself: an SSH remote
(``git@host:org/repo.git``) needs a key, an HTTPS remote needs credentials, and
a local path needs nothing at all. Guessing from configuration instead leads to
building the wrong auth object for the repository at hand.
"""

from enum import Enum

__all__ = ["RemoteScheme", "detect_remote_scheme"]

_SSH_URL_SCHEMES = frozenset({"ssh", "git+ssh"})
_HTTP_URL_SCHEMES = frozenset({"http", "https"})
_SCHEME_SEPARATOR = "://"


class RemoteScheme(Enum):
    """Transport advertised by a git remote URL."""

    SSH = "ssh"
    HTTP = "http"
    LOCAL = "local"
    ANONYMOUS = "anonymous"

    @property
    def needs_auth(self) -> bool:
        """True when the transport requires credentials to reach the remote."""
        return self in (RemoteScheme.SSH, RemoteScheme.HTTP)


def detect_remote_scheme(url: str) -> RemoteScheme:
    """Determine which transport a git remote URL uses.

    Recognises explicit URL schemes (``ssh://``, ``https://``, ``file://``,
    ``git://``) as well as the scp-like shorthand ``[user@]host:path`` used by
    GitHub and Bitbucket remotes.

    Args:
        url: Remote URL or local path.

    Returns:
        The detected transport.

    Raises:
        ValueError: If ``url`` is empty, or uses an unsupported explicit scheme.

    """
    candidate = url.strip()
    if not candidate:
        msg = "Cannot detect the transport of an empty remote URL"
        raise ValueError(msg)

    if _SCHEME_SEPARATOR in candidate:
        return _scheme_from_explicit_url(candidate)

    if _is_scp_like(candidate):
        return RemoteScheme.SSH

    return RemoteScheme.LOCAL


def _scheme_from_explicit_url(url: str) -> RemoteScheme:
    """Map the scheme of an explicit ``scheme://`` URL to a transport."""
    scheme = url.split(_SCHEME_SEPARATOR, 1)[0].lower()

    if scheme in _SSH_URL_SCHEMES:
        return RemoteScheme.SSH
    if scheme in _HTTP_URL_SCHEMES:
        return RemoteScheme.HTTP
    if scheme == "file":
        return RemoteScheme.LOCAL
    if scheme == "git":
        return RemoteScheme.ANONYMOUS

    msg = f"Unsupported git remote scheme '{scheme}' in URL '{url}'"
    raise ValueError(msg)


def _is_scp_like(url: str) -> bool:
    """Tell whether a URL uses the ``[user@]host:path`` shorthand, i.e. SSH.

    An absolute or relative filesystem path is never scp-like, and neither is a
    string whose colon appears after a path separator.
    """
    if url.startswith((".", "/", "~")):
        return False

    host, separator, _ = url.partition(":")
    return bool(separator) and "/" not in host
