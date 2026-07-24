"""Tests for credentials.azure_storage_credentials module."""

import pytest

from credentials.azure_storage_credentials import AzureStorageCredentials
from utils.utils_for_unit_tests import compare


def test_missingenvvars_valid_default_azure_requires_none() -> None:
    creds = AzureStorageCredentials()
    assert compare("eq", creds.missing_env_vars(), [])


def test_missingenvvars_valid_client_secret_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)

    creds = AzureStorageCredentials(credential_type="client_secret")
    assert compare(
        "eq",
        creds.missing_env_vars(),
        ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"],
    )


def test_authkwargs_valid_returns_none() -> None:
    creds = AzureStorageCredentials()
    assert compare("eq", creds.auth_kwargs(), None)


def test_clientsecretkwargs_valid_delegates_to_nested_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")

    creds = AzureStorageCredentials(credential_type="client_secret")
    assert compare(
        "eq",
        creds.client_secret_kwargs(),
        {
            "tenant_id": "tenant",
            "client_id": "client",
            "client_secret": "secret",
        },
    )
