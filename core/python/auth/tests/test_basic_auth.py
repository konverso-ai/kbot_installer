"""Tests for auth.basic_auth module."""

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from auth.basic_auth import BasicAuth
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "params, expected_secret",
    [
        ({"username": "u", "password": SecretStr("p")}, "dTpw"),
        ({"username": "git", "password": SecretStr("token")}, "Z2l0OnRva2Vu"),
    ],
)
def test_encodesecret_valid_base64_credentials(params: dict, expected_secret: str) -> None:
    auth = BasicAuth(**params)
    assert compare("eq", auth.secret.get_secret_value(), expected_secret)


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {"username": "u", "password": SecretStr("p")},
            {"username": "u", "password": "p", "header": "Basic dTpw"},
        ),
        (
            {"username": "git", "password": SecretStr("token")},
            {"username": "git", "password": "token", "header": "Basic Z2l0OnRva2Vu"},
        ),
    ],
)
def test_basicauth_valid_exposes_credentials_and_header(params: dict, expected: dict) -> None:
    auth = BasicAuth(**params)
    kwargs = auth.remote_kwargs()
    assert compare("eq", kwargs["username"], expected["username"])
    assert compare("eq", kwargs["password"], expected["password"])
    assert compare("eq", auth.header_value, expected["header"])


def test_basicauth_valid_reads_credentials_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASIC_AUTH_USERNAME", "envuser")
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", "envpass")
    auth = BasicAuth()
    assert compare("eq", auth.username, "envuser")
    assert compare("eq", auth.password.get_secret_value(), "envpass")


def test_authflow_valid_sets_basic_authorization_header() -> None:
    auth = BasicAuth(username="u", password=SecretStr("p"))
    request = httpx.Request("GET", "https://example.com")
    authenticated = next(auth.auth_flow(request))
    assert compare("eq", authenticated.headers["Authorization"], "Basic dTpw")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"username": "", "password": SecretStr("p")}, ValidationError),
        ({"password": SecretStr("p")}, ValidationError),
        ({"username": "u"}, ValidationError),
    ],
)
def test_basicauth_invalid_rejects_bad_input(params: dict, expected: type[BaseException]) -> None:
    with pytest.raises(expected):
        _ = BasicAuth(**params)
