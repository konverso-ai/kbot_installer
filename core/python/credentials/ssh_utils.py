"""Shared helpers for SSH-key based credential detection."""

import os
from pathlib import Path

from auth.ssh.ssh_auth import DEFAULT_KEY_FILENAMES


def has_ssh_auth_sock() -> bool:
    """Return whether a forwarded SSH agent socket is available.

    Returns:
        True if the ``SSH_AUTH_SOCK`` environment variable is set.

    """
    return bool(os.environ.get("SSH_AUTH_SOCK"))


def has_local_ssh_key(ssh_dir: Path | None = None) -> bool:
    """Return whether a recognized local SSH private key file exists.

    Args:
        ssh_dir: Directory to search for key files. Defaults to ``~/.ssh``.

    Returns:
        True if any of the default SSH key filenames exists in ``ssh_dir``.

    """
    directory = ssh_dir if ssh_dir is not None else Path.home() / ".ssh"
    return any((directory / name).is_file() for name in DEFAULT_KEY_FILENAMES)


def ssh_missing_env_vars() -> list[str]:
    """Return a descriptive message when no SSH authentication source is available.

    Returns:
        An empty list when a local key or forwarded agent is available,
        otherwise a single-item list describing the missing source.

    """
    if has_ssh_auth_sock() or has_local_ssh_key():
        return []

    return [
        "SSH private key in ~/.ssh (id_ed25519, id_rsa, ...) or SSH_AUTH_SOCK",
    ]


def ssh_auth_kwargs() -> dict[str, object]:
    """Return keyword arguments for building an ``SshAuth`` instance.

    Returns:
        Keyword arguments for ``add_ssh_auth("ssh", **kwargs)``: prefers a
        forwarded SSH agent, then a local key, and an empty mapping when
        neither is available.

    """
    if has_ssh_auth_sock():
        return {"username": "git", "use_agent": True}
    if has_local_ssh_key():
        return {"username": "git"}
    return {}
