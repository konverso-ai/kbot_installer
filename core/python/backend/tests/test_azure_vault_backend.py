"""Tests for azure_vault_backend module."""

from unittest.mock import MagicMock, patch

from backend.azure_vault_backend import AzureVaultBackend
from credentials.azure_credentials import AzureCredentials
from utils.utils_for_unit_tests import compare


class TestAzureVaultBackend:
    """Test cases for AzureVaultBackend class."""

    def test_init_valid_builds_client_from_credentials(self) -> None:
        """Test AzureVaultBackend builds a SecretClient from the given credentials."""
        with patch("backend.azure_vault_backend.SecretClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            credentials = MagicMock(spec=AzureCredentials)
            mock_token_credential = MagicMock()
            credentials.get_credential.return_value = mock_token_credential

            backend = AzureVaultBackend(credentials, vault_name="my-vault")

            credentials.get_credential.assert_called_once_with()
            mock_cls.assert_called_once_with(
                vault_url="https://my-vault.vault.azure.net",
                credential=mock_token_credential,
            )
            assert compare("eq", backend.get_client(), mock_client)
