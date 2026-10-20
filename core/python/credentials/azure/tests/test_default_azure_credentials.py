"""Tests for credentials.azure.default_azure_credentials module."""

from unittest.mock import MagicMock, patch

from azure.identity import DefaultAzureCredential

from credentials.azure.default_azure_credentials import default_azure_credentials


def test_default_azure_credentials_valid_returns_instance() -> None:
    """default_azure_credentials should return a DefaultAzureCredential instance."""
    credential = default_azure_credentials()
    assert isinstance(credential, DefaultAzureCredential)


@patch("credentials.azure.default_azure_credentials.DefaultAzureCredential")
def test_default_azure_credentials_valid_constructs_without_args(
    mock_credential_cls: MagicMock,
) -> None:
    """default_azure_credentials should construct DefaultAzureCredential with no args."""
    mock_instance = MagicMock(spec=DefaultAzureCredential)
    mock_credential_cls.return_value = mock_instance

    result = default_azure_credentials()

    mock_credential_cls.assert_called_once_with()
    assert result is mock_instance
