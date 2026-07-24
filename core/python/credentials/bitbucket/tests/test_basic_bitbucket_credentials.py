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
