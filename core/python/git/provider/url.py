"""Pure helper for building git repository URLs.

Kept independent of any provider instance so it can be unit tested and
reused without constructing a full ``GitProviderBase`` subclass.
"""

from auth.ssh.ssh_auth import SshAuth
from git.auth_protocol import GitAuthProtocol


def build_git_url(
    *,
    name: str,
    account_name: str,
    repository_name: str,
    base_url: str,
    ssh_host: str,
    auth: GitAuthProtocol | None,
) -> str:
    """Build the remote repository URL for the given auth mode.

    Args:
        name: Provider name (e.g. ``"github"``), used to fill the ``{name}``
            placeholder in ``base_url``.
        account_name: Account or organization owning the repository.
        repository_name: Short repository name.
        base_url: HTTPS URL template with ``{name}``, ``{account_name}`` and
            ``{repository_name}`` placeholders, used when not authenticating
            over SSH.
        ssh_host: Hostname to use when building an SSH URL.
        auth: Authentication object in use. SSH URLs are built when this is
            an instance of ``SshAuth``, HTTPS URLs otherwise.

    Returns:
        The HTTPS or SSH URL to use for git operations.

    Raises:
        ValueError: If ``account_name`` or (for HTTPS) ``base_url`` is empty.

    """
    if not account_name:
        msg = "Provider cannot build a repository URL: account_name is required"
        raise ValueError(msg)

    if isinstance(auth, SshAuth):
        return f"git@{ssh_host}:{account_name}/{repository_name}.git"

    if not base_url:
        msg = "Provider cannot build a repository URL: base_url is required"
        raise ValueError(msg)
    return base_url.format(
        name=name, account_name=account_name, repository_name=repository_name
    )
