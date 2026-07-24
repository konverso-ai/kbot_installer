"""Tests for auth.bearer_auth module."""

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from auth.bearer_auth import BearerAuth
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"secret": SecretStr("my-token")}, "Bearer my-token"),
        ({"secret": SecretStr("abc123")}, "Bearer abc123"),
    ],
)
def test_bearerauth_valid_formats_bearer_header(params: dict, expected: str) -> None:
    auth = BearerAuth(**params)
    assert compare("eq", auth.header_value, expected)
    assert compare("eq", auth.prefix, "Bearer")


def test_authflow_valid_sets_authorization_header() -> None:
    auth = BearerAuth(secret=SecretStr("my-token"))
    request = httpx.Request("GET", "https://example.com")
    authenticated = next(auth.auth_flow(request))
    assert compare("eq", authenticated.headers["Authorization"], "Bearer my-token")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"secret": SecretStr("")}, ValidationError),
        ({}, ValidationError),
    ],
)
def test_bearerauth_invalid_rejects_bad_secret(params: dict, expected: type[BaseException]) -> None:
    with pytest.raises(expected):
        _ = BearerAuth(**params)
