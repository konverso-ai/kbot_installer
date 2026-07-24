"""Tests for credentials.azure_credentials module."""

from unittest.mock import patch

from azure.identity import DefaultAzureCredential

from credentials.azure_credentials import AzureCredentials
from utils.utils_for_unit_tests import compare


def test_missingenvvars_valid_always_empty() -> None:
    """Test missing_env_vars always reports nothing missing (default credentials)."""
    creds = AzureCredentials()
    assert compare("eq", creds.missing_env_vars(), [])


def test_accounturl_valid_defaults_to_none() -> None:
    """Test account_url defaults to None when not provided."""
    creds = AzureCredentials()
    assert creds.account_url is None


def test_containername_valid_defaults_to_none() -> None:
    """Test container_name defaults to None when not provided."""
    creds = AzureCredentials()
    assert creds.container_name is None


def test_fields_valid_accept_explicit_values() -> None:
    """Test account_url and container_name accept explicit constructor values."""
    creds = AzureCredentials(
        account_url="https://account.blob.core.windows.net",
        container_name="container",
    )
    assert compare("eq", creds.account_url, "https://account.blob.core.windows.net")
    assert compare("eq", creds.container_name, "container")


def test_getcredential_valid_returns_default_azure_credential() -> None:
    """Test get_credential builds a DefaultAzureCredential instance."""
    with patch("credentials.azure_credentials.DefaultAzureCredential") as mock_cls:
        mock_instance = mock_cls.return_value
        creds = AzureCredentials()

        result = creds.get_credential()

        mock_cls.assert_called_once_with()
        assert compare("eq", result, mock_instance)


def test_getcredential_valid_returns_token_credential_type() -> None:
    """Test get_credential returns an actual DefaultAzureCredential when unmocked."""
    creds = AzureCredentials()
    assert isinstance(creds.get_credential(), DefaultAzureCredential)
