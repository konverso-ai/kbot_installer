"""Tests for credentials.ssh_credentials module."""

import os
from pathlib import Path
from unittest.mock import patch

from credentials.ssh_credentials import SshCredentials


@patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
@patch("credentials.ssh_credentials.Path.home")
def test_auth_kwargs_uses_agent_when_only_sock_is_available(mock_home: object) -> None:
    """Forwarded SSH agent should enable agent mode when no local keys exist."""
    mock_home.return_value = Path("/empty/home")
    creds = SshCredentials()

    assert creds.missing_env_vars() == []
    assert creds.auth_kwargs() == {"username": "git", "use_agent": True}


@patch.dict(os.environ, {}, clear=True)
def test_auth_kwargs_uses_local_key_when_present(tmp_path: Path) -> None:
    """Local SSH keys should take precedence over a forwarded agent."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_text("private-key")

    with (
        patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True),
        patch("credentials.ssh_credentials.Path.home", return_value=tmp_path),
    ):
        creds = SshCredentials()
        assert creds.missing_env_vars() == []
        assert creds.auth_kwargs() == {"username": "git"}


@patch("credentials.ssh_credentials.Path.home")
@patch.dict(os.environ, {}, clear=True)
def test_auth_kwargs_none_when_no_source_available(mock_home: object) -> None:
    """No SSH source should report missing credentials."""
    mock_home.return_value = Path("/empty/home")
    creds = SshCredentials()

    assert creds.missing_env_vars() != []
    assert creds.auth_kwargs() is None
