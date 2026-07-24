"""Tests for credentials.bitbucket_credentials module."""

import pytest

from credentials.bitbucket_credentials import BitbucketCredentials
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

    creds = BitbucketCredentials()
    assert compare("eq", creds.missing_env_vars(), expected_missing)


@pytest.mark.parametrize(
    "env, expected_auth",
    [
        ({}, None),
        (
            {
                "BITBUCKET_USERNAME": "user",
                "BITBUCKET_APP_PASSWORD": "app-password",
            },
            {"username": "user", "password": "app-password"},
        ),
    ],
)
def test_authkwargs_valid_returns_credentials(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    expected_auth: dict[str, str] | None,
) -> None:
    for key in ("BITBUCKET_USERNAME", "BITBUCKET_APP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    creds = BitbucketCredentials()
    assert compare("eq", creds.auth_kwargs(), expected_auth)
