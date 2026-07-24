"""Tests for oci_backend module."""

from unittest.mock import MagicMock, patch

from backend.oci_backend import OciBackend
from utils.utils_for_unit_tests import compare


class TestOciBackend:
    """Test cases for OciBackend class."""

    def test_init_valid_builds_client_from_config(self) -> None:
        """Test OciBackend builds an ObjectStorageClient from the given credentials."""
        with patch("backend.oci_backend.oci") as mock_oci:
            mock_client = MagicMock()
            mock_oci.object_storage.ObjectStorageClient.return_value = mock_client

            backend = OciBackend(
                region="eu-frankfurt-1",
                user_ocid="ocid1.user.oc1..aaa",
                tenancy_ocid="ocid1.tenancy.oc1..bbb",
                fingerprint="20:3b:97:13:55:1c:5b:0d:d3:37:d8:50:4e:c5:3a:34",
                private_key_path="/tmp/key.pem",
                pass_phrase="secret",
            )

            mock_oci.object_storage.ObjectStorageClient.assert_called_once_with(
                {
                    "user": "ocid1.user.oc1..aaa",
                    "tenancy": "ocid1.tenancy.oc1..bbb",
                    "fingerprint": "20:3b:97:13:55:1c:5b:0d:d3:37:d8:50:4e:c5:3a:34",
                    "key_file": "/tmp/key.pem",
                    "region": "eu-frankfurt-1",
                    "pass_phrase": "secret",
                }
            )
            assert compare("eq", backend.get_client(), mock_client)
