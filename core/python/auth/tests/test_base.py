"""Tests for auth.base module."""

import pytest
from pydantic import SecretStr

from auth.base import AuthBase
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "params, expected",
    [
        ({}, {"header_name": "Authorization", "prefix": "", "secret": ""}),
        (
            {"header_name": "X-Custom", "prefix": "Token", "secret": SecretStr("abc")},
            {"header_name": "X-Custom", "prefix": "Token", "secret": "abc"},
        ),
    ],
)
def test_authbase_valid_default_fields(params: dict, expected: dict) -> None:
    auth = AuthBase(**params)
    assert compare("eq", auth.header_name, expected["header_name"])
    assert compare("eq", auth.prefix, expected["prefix"])
    assert compare("eq", auth.secret.get_secret_value(), expected["secret"])
