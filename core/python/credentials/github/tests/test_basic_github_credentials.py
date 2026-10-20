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


def test_authkwargs_valid_returns_default_username_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test auth_kwargs defaults username to x-access-token when unset."""
    monkeypatch.delenv("GITHUB_USERNAME", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "gh-token")

    creds = BasicGithubCredentials()
    assert compare(
        "eq",
        creds.auth_kwargs(),
        {"username": "x-access-token", "password": "gh-token"},
    )


def test_authkwargs_valid_returns_configured_username(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test auth_kwargs uses the configured username when set."""
    monkeypatch.setenv("GITHUB_USERNAME", "octocat")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-token")

    creds = BasicGithubCredentials()
    assert compare(
        "eq",
        creds.auth_kwargs(),
        {"username": "octocat", "password": "gh-token"},
    )


def test_authkwargs_invalid_returns_empty_when_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test auth_kwargs returns an empty dict when GITHUB_TOKEN is unset."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    creds = BasicGithubCredentials()
    assert compare("eq", creds.auth_kwargs(), {})
