"""Tests for credentials.ssh_utils module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from credentials.ssh_utils import (
    has_local_ssh_key,
    has_ssh_auth_sock,
    ssh_auth_kwargs,
    ssh_missing_env_vars,
)
from utils.utils_for_unit_tests import compare


def test_hassshauthsock_valid_true_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test has_ssh_auth_sock returns True when SSH_AUTH_SOCK is set."""
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/ssh-agent")
    assert has_ssh_auth_sock() is True


def test_hassshauthsock_valid_false_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test has_ssh_auth_sock returns False when SSH_AUTH_SOCK is unset."""
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    assert has_ssh_auth_sock() is False


def test_haslocalsshkey_valid_true_when_key_file_exists(tmp_path: Path) -> None:
    """Test has_local_ssh_key returns True when a recognized key file exists."""
    (tmp_path / "id_ed25519").write_text("private-key")
    assert has_local_ssh_key(tmp_path) is True


def test_haslocalsshkey_valid_false_when_directory_empty(tmp_path: Path) -> None:
    """Test has_local_ssh_key returns False when no recognized key file exists."""
    assert has_local_ssh_key(tmp_path) is False


def test_haslocalsshkey_valid_defaults_to_home_ssh_dir(tmp_path: Path) -> None:
    """Test has_local_ssh_key defaults to searching ~/.ssh when unset."""
    with patch("credentials.ssh_utils.Path.home", return_value=tmp_path):
        assert has_local_ssh_key() is False


@patch.dict(os.environ, {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
def test_sshauthkwargs_valid_prefers_forwarded_agent(tmp_path: Path) -> None:
    """Test ssh_auth_kwargs prefers a forwarded SSH agent over a local key."""
    with patch("credentials.ssh_utils.Path.home", return_value=tmp_path):
        assert compare(
            "eq",
            ssh_auth_kwargs(),
            {"username": "git", "use_agent": True},
        )


@patch.dict(os.environ, {}, clear=True)
def test_sshauthkwargs_valid_uses_local_key_when_no_agent(tmp_path: Path) -> None:
    """Test ssh_auth_kwargs falls back to a local key when no agent is forwarded."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_rsa").write_text("private-key")
    with patch("credentials.ssh_utils.Path.home", return_value=tmp_path):
        assert compare("eq", ssh_auth_kwargs(), {"username": "git"})


@patch.dict(os.environ, {}, clear=True)
def test_sshauthkwargs_invalid_empty_when_no_source_available(tmp_path: Path) -> None:
    """Test ssh_auth_kwargs returns an empty dict when no SSH source is available."""
    with patch("credentials.ssh_utils.Path.home", return_value=tmp_path):
        assert compare("eq", ssh_auth_kwargs(), {})


@patch.dict(os.environ, {}, clear=True)
def test_sshmissingenvvars_invalid_nonempty_when_no_source_available(
    tmp_path: Path,
) -> None:
    """Test ssh_missing_env_vars reports a message when no SSH source is available."""
    with patch("credentials.ssh_utils.Path.home", return_value=tmp_path):
        assert len(ssh_missing_env_vars()) == 1
