"""Tests for oci_vault module."""

import base64
from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from vault.oci_vault import OciVault


@pytest.fixture
def oci_client() -> MagicMock:
    """Create a mock OCI Secrets client."""
    return MagicMock()


@pytest.fixture
def backend(oci_client: MagicMock) -> MagicMock:
    """Create a mock OCI Vault backend."""
    mock_backend = MagicMock()
    mock_backend.get_client.return_value = oci_client
    return mock_backend


@pytest.fixture
def vault(backend: MagicMock) -> OciVault:
    """Create an OciVault instance for testing."""
    return OciVault(backend=backend)


class TestOciVault:
    """Test cases for OciVault class."""

    def test_get_valid_returns_decoded_secret_value(
        self, vault: OciVault, oci_client: MagicMock
    ) -> None:
        """Test get calls get_secret_bundle_by_name and decodes the base64 content."""
        encoded_content = base64.b64encode(b"super-secret").decode("ascii")
        response = MagicMock()
        response.data.secret_bundle_content.content = encoded_content
        oci_client.get_secret_bundle_by_name.return_value = response

        result = vault.get("ocid1.vault.oc1..xxx::db-password")

        oci_client.get_secret_bundle_by_name.assert_called_once_with(
            secret_name="db-password", vault_id="ocid1.vault.oc1..xxx"
        )
        assert compare("eq", result, "super-secret")

    def test_get_invalid_raises_value_error_on_malformed_key(
        self, vault: OciVault
    ) -> None:
        """Test get propagates ValueError for a malformed key."""
        with pytest.raises(ValueError, match="Invalid vault key"):
            vault.get("no-separator")

    def test_get_invalid_raises_runtime_error_without_client(self) -> None:
        """Test get raises RuntimeError when the backend has no client."""
        backend = MagicMock()
        backend.get_client.return_value = None
        vault = OciVault(backend=backend)

        with pytest.raises(RuntimeError, match="OCI Secrets client unavailable"):
            vault.get("ocid1.vault.oc1..xxx::db-password")
