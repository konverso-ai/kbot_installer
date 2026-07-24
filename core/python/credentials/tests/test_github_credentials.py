"""Tests for credentials.github_credentials module."""

import pytest

from credentials.github_credentials import GithubCredentials
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

    creds = GithubCredentials()
    assert compare("eq", creds.missing_env_vars(), expected_missing)


@pytest.mark.parametrize(
    "env, expected_auth",
    [
        ({}, None),
        (
            {"GITHUB_TOKEN": "gh-token"},
            {"username": "git", "password": "gh-token"},
        ),
    ],
)
def test_authkwargs_valid_returns_credentials(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    expected_auth: dict[str, str] | None,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    creds = GithubCredentials()
    assert compare("eq", creds.auth_kwargs(), expected_auth)
