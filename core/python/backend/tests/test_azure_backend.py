"""Tests for azure_backend module."""

from unittest.mock import MagicMock, patch

from backend.azure_backend import AzureBackend
from credentials.azure_credentials import AzureCredentials
from utils.utils_for_unit_tests import compare


class TestAzureBackend:
    """Test cases for AzureBackend class."""

    def test_init_valid_builds_client_from_credentials(self) -> None:
        """Test AzureBackend builds a BlobServiceClient from the given credentials."""
        with patch("backend.azure_backend.BlobServiceClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            credentials = MagicMock(spec=AzureCredentials)
            credentials.account_url = "https://account.blob.core.windows.net"
            mock_token_credential = MagicMock()
            credentials.get_credential.return_value = mock_token_credential

            backend = AzureBackend(credentials)

            credentials.get_credential.assert_called_once_with()
            mock_cls.assert_called_once_with(
                account_url="https://account.blob.core.windows.net",
                credential=mock_token_credential,
            )
            assert compare("eq", backend.get_client(), mock_client)
