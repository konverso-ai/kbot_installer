"""Tests for credentials.s3_credentials module."""

import pytest

from credentials.s3_credentials import S3Credentials
from utils.utils_for_unit_tests import compare


def test_missingenvvars_valid_always_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test missing_env_vars always reports nothing missing (default credentials)."""
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    creds = S3Credentials()
    assert compare("eq", creds.missing_env_vars(), [])


def test_regionname_valid_defaults_to_eu_west_1() -> None:
    """Test region_name defaults to eu-west-1 when AWS_DEFAULT_REGION is unset."""
    creds = S3Credentials()
    assert compare("eq", creds.region_name, "eu-west-1")


def test_regionname_valid_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test region_name is read from AWS_DEFAULT_REGION when set."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    creds = S3Credentials()
    assert compare("eq", creds.region_name, "eu-central-1")


def test_endpointurl_valid_defaults_to_none() -> None:
    """Test endpoint_url defaults to None when unset."""
    creds = S3Credentials()
    assert creds.endpoint_url is None


def test_poolandretry_valid_default_values() -> None:
    """Test max_pool_connections and retry_max_attempts default values."""
    creds = S3Credentials()
    assert compare("eq", creds.max_pool_connections, 10)
    assert compare("eq", creds.retry_max_attempts, 3)
