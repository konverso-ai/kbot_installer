"""Tests for the auth package's top-level ``create_auth`` re-export."""

import pytest
from pydantic import SecretStr

from auth import create_auth
from auth.http.basic_auth import BasicAuth
from auth.ssh.factory import add_ssh_auth
from auth.ssh.ssh_auth import SshAuth
from utils.utils_for_unit_tests import compare


def test_createauth_valid_builds_auth_instance() -> None:
    auth = create_auth("basic", username="u", password=SecretStr("p"))
    assert compare("eq", isinstance(auth, BasicAuth), True)


def test_createauth_invalid_unknown_name() -> None:
    with pytest.raises(ImportError):
        _ = create_auth("unknown")


def test_addsshauth_valid_builds_ssh_auth_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/fake-agent.sock")
    auth = add_ssh_auth("ssh", use_agent=True)
    assert compare("eq", isinstance(auth, SshAuth), True)
