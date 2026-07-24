"""Tests for auth.factory module."""

import pytest
from pydantic import SecretStr

from auth.apikey_auth import ApikeyAuth
from auth.basic_auth import BasicAuth
from auth.bearer_auth import BearerAuth
from auth.factory import create_auth
from auth.ssh.factory import add_ssh_auth
from auth.ssh.ssh_auth import SshAuth
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "name, params, expected_type",
    [
        (
            "basic",
            {"username": "u", "password": SecretStr("p")},
            BasicAuth,
        ),
        ("bearer", {"secret": SecretStr("token")}, BearerAuth),
        ("apikey", {"secret": SecretStr("key")}, ApikeyAuth),
    ],
)
def test_createauth_valid_builds_auth_instance(
    name: str,
    params: dict,
    expected_type: type,
) -> None:
    auth = create_auth(name, **params)
    assert compare("eq", isinstance(auth, expected_type), True)


def test_addsshauth_valid_builds_ssh_auth_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/fake-agent.sock")
    auth = add_ssh_auth("ssh", use_agent=True)
    assert compare("eq", isinstance(auth, SshAuth), True)


@pytest.mark.parametrize(
    "name, params, expected",
    [
        ("unknown", {}, ImportError),
    ],
)
def test_createauth_invalid_unknown_name(
    name: str, params: dict, expected: type[BaseException]
) -> None:
    with pytest.raises(expected):
        _ = create_auth(name, **params)
