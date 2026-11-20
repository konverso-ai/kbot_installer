"""Tests for oci_storage_backend module."""

from unittest.mock import MagicMock, patch

from backend.oci_storage_backend import OciStorageBackend
from credentials.oci_credentials import OciCredentials
from utils.utils_for_unit_tests import compare


class TestOciStorageBackend:
    """Test cases for OciStorageBackend class."""

    def test_init_valid_builds_client_from_credentials(self) -> None:
        """Test OciStorageBackend builds an ObjectStorageClient from the given credentials."""
        with patch("backend.oci_storage_backend.oci") as mock_oci:
            mock_client = MagicMock()
            mock_oci.object_storage.ObjectStorageClient.return_value = mock_client

            credentials = MagicMock(spec=OciCredentials)
            credentials.to_client_config.return_value = {
                "region": "eu-frankfurt-1",
            }

            backend = OciStorageBackend(credentials)

            credentials.to_client_config.assert_called_once_with()
            mock_oci.object_storage.ObjectStorageClient.assert_called_once_with(
                {"region": "eu-frankfurt-1"}
            )
            assert compare("eq", backend.get_client(), mock_client)
