"""Tests for credentials.hashicorp_credentials module."""

import pytest

from credentials.hashicorp_credentials import HashicorpCredentials
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "env, expected_missing",
    [
        ({}, ["VAULT_ADDR", "VAULT_TOKEN"]),
        ({"VAULT_ADDR": "https://vault.example.com:8200", "VAULT_TOKEN": "s.token"}, []),
        ({"VAULT_ADDR": "https://vault.example.com:8200"}, ["VAULT_TOKEN"]),
        ({"VAULT_TOKEN": "s.token"}, ["VAULT_ADDR"]),
    ],
)
def test_missingenvvars_valid_reports_gaps(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    expected_missing: list[str],
) -> None:
    """Test missing_env_vars reports VAULT_ADDR/VAULT_TOKEN gaps."""
    for key in ("VAULT_ADDR", "VAULT_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    assert compare("eq", HashicorpCredentials().missing_env_vars(), expected_missing)
