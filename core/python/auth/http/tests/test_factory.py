"""Tests for auth.http.factory module."""

import pytest
from pydantic import SecretStr

from auth.http.apikey_auth import ApikeyAuth
from auth.http.basic_auth import BasicAuth
from auth.http.bearer_auth import BearerAuth
from auth.http.factory import add_http_auth
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
def test_addhttpauth_valid_builds_auth_instance(
    name: str,
    params: dict,
    expected_type: type,
) -> None:
    auth = add_http_auth(name, **params)
    assert compare("eq", isinstance(auth, expected_type), True)


@pytest.mark.parametrize(
    "name, params, expected",
    [
        ("unknown", {}, ImportError),
    ],
)
def test_addhttpauth_invalid_unknown_name(
    name: str, params: dict, expected: type[BaseException]
) -> None:
    with pytest.raises(expected):
        _ = add_http_auth(name, **params)
