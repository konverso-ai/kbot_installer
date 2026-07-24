"""Tests for auth.auth_mixin module."""

import httpx
import pytest
from pydantic import SecretStr

from auth.auth_mixin import AuthMixin
from auth.base import RequiredSecret
from utils.utils_for_unit_tests import compare


class _ExampleAuth(AuthMixin):
    secret: RequiredSecret


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"secret": SecretStr("token"), "prefix": "Bearer"}, "Bearer token"),
        ({"secret": SecretStr("raw-key"), "prefix": ""}, "raw-key"),
        (
            {"secret": SecretStr("k"), "prefix": "APIKey", "header_name": "X-Api-Key"},
            "APIKey k",
        ),
    ],
)
def test_headervalue_valid_formats_header(params: dict, expected: str) -> None:
    auth = _ExampleAuth(**params)
    assert compare("eq", auth.header_value, expected)


@pytest.mark.parametrize(
    "params, expected_header, expected_value",
    [
        (
            {"secret": SecretStr("my-token"), "prefix": "Bearer"},
            "Authorization",
            "Bearer my-token",
        ),
        (
            {
                "secret": SecretStr("key"),
                "prefix": "APIKey",
                "header_name": "X-Api-Key",
            },
            "X-Api-Key",
            "APIKey key",
        ),
    ],
)
def test_authflow_valid_sets_request_header(
    params: dict, expected_header: str, expected_value: str
) -> None:
    auth = _ExampleAuth(**params)
    request = httpx.Request("GET", "https://example.com")
    authenticated = next(auth.auth_flow(request))
    assert compare("eq", authenticated.headers[expected_header], expected_value)


def test_remotekwargs_valid_returns_empty_dict() -> None:
    auth = _ExampleAuth(secret=SecretStr("token"), prefix="Bearer")
    assert compare("eq", auth.remote_kwargs(), {})
