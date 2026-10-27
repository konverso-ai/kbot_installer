"""Tests for credentials.bitbucket.basic_bitbucket_credentials module."""

import pytest

from credentials.bitbucket.basic_bitbucket_credentials import (
    BasicBitbucketCredentials,
)
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "env, expected_missing",
    [
        ({}, ["BITBUCKET_USERNAME", "BITBUCKET_APP_PASSWORD"]),
        (
            {
                "BITBUCKET_USERNAME": "user",
                "BITBUCKET_APP_PASSWORD": "app-password",
            },
            [],
        ),
    ],
)
def test_missingenvvars_valid_reports_gaps(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    expected_missing: list[str],
) -> None:
    for key in ("BITBUCKET_USERNAME", "BITBUCKET_APP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    creds = BasicBitbucketCredentials()
    assert compare("eq", creds.missing_env_vars(), expected_missing)


def test_authkwargs_valid_returns_username_and_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test auth_kwargs returns username/password when both are set."""
    monkeypatch.setenv("BITBUCKET_USERNAME", "user")
    monkeypatch.setenv("BITBUCKET_APP_PASSWORD", "app-password")

    creds = BasicBitbucketCredentials()
    assert compare(
        "eq",
        creds.auth_kwargs(),
        {"username": "user", "password": "app-password"},
    )


def test_authkwargs_invalid_returns_empty_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test auth_kwargs returns an empty dict when credentials are incomplete."""
    monkeypatch.delenv("BITBUCKET_USERNAME", raising=False)
    monkeypatch.delenv("BITBUCKET_APP_PASSWORD", raising=False)

    creds = BasicBitbucketCredentials()
    assert compare("eq", creds.auth_kwargs(), {})
