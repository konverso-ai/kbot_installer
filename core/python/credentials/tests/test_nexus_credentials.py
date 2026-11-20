"""Tests for credentials.nexus_credentials module."""

import pytest

from credentials.nexus_credentials import NexusCredentials
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "env, expected_missing",
    [
        ({}, ["NEXUS_USERNAME", "NEXUS_PASSWORD"]),
        (
            {"NEXUS_USERNAME": "user", "NEXUS_PASSWORD": "password"},
            [],
        ),
        ({"NEXUS_USERNAME": "user"}, ["NEXUS_PASSWORD"]),
        ({"NEXUS_PASSWORD": "password"}, ["NEXUS_USERNAME"]),
    ],
)
def test_missingenvvars_valid_reports_gaps(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    expected_missing: list[str],
) -> None:
    """Test missing_env_vars reports NEXUS_USERNAME/NEXUS_PASSWORD gaps."""
    for key in ("NEXUS_USERNAME", "NEXUS_USER", "NEXUS_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    creds = NexusCredentials()
    assert compare("eq", creds.missing_env_vars(), expected_missing)


def test_username_valid_reads_nexus_user_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test username can also be read from the NEXUS_USER alias."""
    monkeypatch.delenv("NEXUS_USERNAME", raising=False)
    monkeypatch.setenv("NEXUS_USER", "user")

    creds = NexusCredentials()
    assert compare("eq", creds.username, "user")


def test_authkwargs_valid_returns_username_and_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test auth_kwargs returns username/password when both are set."""
    monkeypatch.setenv("NEXUS_USERNAME", "user")
    monkeypatch.setenv("NEXUS_PASSWORD", "password")

    creds = NexusCredentials()
    assert compare(
        "eq",
        creds.auth_kwargs(),
        {"username": "user", "password": "password"},
    )


def test_authkwargs_invalid_returns_empty_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test auth_kwargs returns an empty dict when credentials are incomplete."""
    monkeypatch.delenv("NEXUS_USERNAME", raising=False)
    monkeypatch.delenv("NEXUS_USER", raising=False)
    monkeypatch.delenv("NEXUS_PASSWORD", raising=False)

    creds = NexusCredentials()
    assert compare("eq", creds.auth_kwargs(), {})
