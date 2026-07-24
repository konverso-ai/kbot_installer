"""Tests for credentials.github.basic_github_credentials module."""

import pytest

from credentials.github.basic_github_credentials import BasicGithubCredentials
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "env, expected_missing",
    [
        ({}, ["GITHUB_TOKEN"]),
        ({"GITHUB_TOKEN": "gh-token"}, []),
    ],
)
def test_missingenvvars_valid_reports_gaps(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    expected_missing: list[str],
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    creds = BasicGithubCredentials()
    assert compare("eq", creds.missing_env_vars(), expected_missing)
