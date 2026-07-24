"""Tests for credentials.azure_client_secret_credentials module."""

import pytest

from credentials.azure_client_secret_credentials import AzureClientSecretCredentials
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "env, expected_missing",
    [
        (
            {},
            ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"],
        ),
        (
            {
                "AZURE_TENANT_ID": "tenant",
                "AZURE_CLIENT_ID": "client",
                "AZURE_CLIENT_SECRET": "secret",
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
    for key in (
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    creds = AzureClientSecretCredentials()
    assert compare("eq", creds.missing_env_vars(), expected_missing)


def test_authkwargs_valid_returns_none() -> None:
    creds = AzureClientSecretCredentials()
    assert compare("eq", creds.auth_kwargs(), None)


def test_clientsecretkwargs_valid_dumps_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")

    creds = AzureClientSecretCredentials()
    assert compare(
        "eq",
        creds.client_secret_kwargs(),
        {
            "tenant_id": "tenant",
            "client_id": "client",
            "client_secret": "secret",
        },
    )
