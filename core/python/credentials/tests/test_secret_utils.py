"""Tests for credentials.secret_utils module."""

from pydantic import SecretStr

from credentials.secret_utils import secret_value
from utils.utils_for_unit_tests import compare


def test_secretvalue_valid_unwraps_secret_str() -> None:
    """Test secret_value returns the plain string value of a SecretStr."""
    assert compare("eq", secret_value(SecretStr("s3cr3t")), "s3cr3t")


def test_secretvalue_valid_returns_none_when_none() -> None:
    """Test secret_value returns None when given None."""
    assert secret_value(None) is None
