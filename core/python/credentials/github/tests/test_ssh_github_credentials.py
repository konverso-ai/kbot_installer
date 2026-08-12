"""Tests for credentials.github.ssh_github_credentials module."""

import os
from pathlib import Path
from unittest.mock import patch

from credentials.github.ssh_github_credentials import SshGithubCredentials


@patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
@patch("credentials.ssh_utils.Path.home")
def test_missing_env_vars_empty_when_agent_only_sock_is_available(mock_home: object) -> None:
    """Forwarded SSH agent should enable agent mode when no local keys exist."""
    mock_home.return_value = Path("/empty/home")
    creds = SshGithubCredentials()

    assert creds.missing_env_vars() == []


@patch.dict(os.environ, {}, clear=True)
def test_missing_env_vars_empty_when_local_key_is_present(tmp_path: Path) -> None:
    """Local SSH keys should take precedence over a forwarded agent."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_text("private-key")

    with (
        patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True),
        patch("credentials.ssh_utils.Path.home", return_value=tmp_path),
    ):
        creds = SshGithubCredentials()
        assert creds.missing_env_vars() == []


@patch("credentials.ssh_utils.Path.home")
@patch.dict(os.environ, {}, clear=True)
def test_missing_env_vars_nonempty_when_no_source_available(mock_home: object) -> None:
    """No SSH source should report missing credentials."""
    mock_home.return_value = Path("/empty/home")
    creds = SshGithubCredentials()

    assert creds.missing_env_vars() != []


@patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
@patch("credentials.ssh_utils.Path.home")
def test_auth_kwargs_valid_uses_forwarded_agent(mock_home: object) -> None:
    """auth_kwargs should prefer a forwarded SSH agent when available."""
    mock_home.return_value = Path("/empty/home")
    creds = SshGithubCredentials()

    assert creds.auth_kwargs() == {"username": "git", "use_agent": True}
