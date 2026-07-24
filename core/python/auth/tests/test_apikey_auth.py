"""Tests for auth.apikey_auth module."""

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from auth.apikey_auth import ApikeyAuth
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "params, expected_header, expected_value",
    [
        (
            {"secret": SecretStr("my-key")},
            "X-Api-Key",
            "APIKey my-key",
        ),
        (
            {"secret": SecretStr("k"), "header_name": "X-Api-Key"},
            "X-Api-Key",
            "APIKey k",
        ),
    ],
)
def test_apikeyauth_valid_uses_api_key_header(
    params: dict, expected_header: str, expected_value: str
) -> None:
    auth = ApikeyAuth(**params)
    assert compare("eq", auth.header_name, expected_header)
    assert compare("eq", auth.header_value, expected_value)
    assert compare("eq", auth.prefix, "APIKey")


def test_authflow_valid_sets_x_api_key_header() -> None:
    auth = ApikeyAuth(secret=SecretStr("secret-key"))
    request = httpx.Request("GET", "https://example.com")
    authenticated = next(auth.auth_flow(request))
    assert compare("eq", authenticated.headers["X-Api-Key"], "APIKey secret-key")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"secret": SecretStr("")}, ValidationError),
        ({}, ValidationError),
    ],
)
def test_apikeyauth_invalid_rejects_bad_secret(params: dict, expected: type[BaseException]) -> None:
    with pytest.raises(expected):
        _ = ApikeyAuth(**params)
