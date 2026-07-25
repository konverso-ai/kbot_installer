"""Tests for the auth.factory module's add_auth dispatcher."""

from unittest.mock import MagicMock, patch

import pytest

from auth import add_auth
from auth.http.basic_auth import BasicAuth
from auth.ssh.factory import add_ssh_auth
from auth.ssh.ssh_auth import SshAuth
from utils.utils_for_unit_tests import compare


def test_addauth_valid_builds_auth_instance() -> None:
    auth = add_auth("basic", username="u", password="p")  # noqa: S106
    assert compare("eq", isinstance(auth, BasicAuth), True)


def test_addauth_invalid_unknown_name() -> None:
    with pytest.raises(ImportError):
        _ = add_auth("unknown")


def test_addauth_dispatches_ssh_to_add_ssh_auth() -> None:
    """Test that "ssh" auth_type is dispatched to add_ssh_auth."""
    mock_auth = MagicMock()

    with patch("auth.factory.add_ssh_auth", return_value=mock_auth) as mock_add_ssh_auth:
        result = add_auth("ssh", username="git")

        mock_add_ssh_auth.assert_called_once_with("ssh", username="git")
        assert result is mock_auth


def test_addauth_dispatches_other_transports_to_add_http_auth() -> None:
    """Test that non-ssh auth_type is dispatched to add_http_auth."""
    mock_auth = MagicMock()

    with patch("auth.factory.add_http_auth", return_value=mock_auth) as mock_add_http_auth:
        result = add_auth("basic", username="user", password="pass")  # noqa: S106

        mock_add_http_auth.assert_called_once_with("basic", username="user", password="pass")
        assert result is mock_auth


def test_addsshauth_valid_builds_ssh_auth_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/fake-agent.sock")
    auth = add_ssh_auth("ssh", use_agent=True)
    assert compare("eq", isinstance(auth, SshAuth), True)
