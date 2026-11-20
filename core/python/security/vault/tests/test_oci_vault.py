"""Tests for oci_vault module."""

import base64
import json
from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.oci_vault import OciVault

SECRET_OCID = "ocid1.vaultsecret.oc1..xxx"


def _bundle(content: bytes) -> MagicMock:
    """Build an OCI secret bundle response holding ``content``."""
    response = MagicMock()
    response.data.secret_bundle_content.content = base64.b64encode(content).decode(
        "ascii"
    )
    return response


@pytest.fixture
def oci_client() -> MagicMock:
    """Create a mock OCI Secrets client returning a JSON secret."""
    client = MagicMock()
    client.get_secret_bundle.return_value = _bundle(b'{"db-password": "super-secret"}')
    return client


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

    def test_get_valid_returns_json_field_of_secret_ocid(
        self, vault: OciVault, oci_client: MagicMock
    ) -> None:
        """Test get reads the secret by OCID and returns the requested field."""
        result = vault.get(f"{SECRET_OCID}::db-password")

        oci_client.get_secret_bundle.assert_called_once_with(secret_id=SECRET_OCID)
        assert compare("eq", result, "super-secret")

    def test_get_valid_resolves_secret_alias_to_ocid(
        self, backend: MagicMock, oci_client: MagicMock
    ) -> None:
        """Test a non-OCID secret reference is resolved through resolve_secret_id."""
        resolve = MagicMock(return_value=SECRET_OCID)
        vault = OciVault(backend=backend, resolve_secret_id=resolve)

        result = vault.get("oci_global_secret_store::db-password")

        resolve.assert_called_once_with("oci_global_secret_store")
        oci_client.get_secret_bundle.assert_called_once_with(secret_id=SECRET_OCID)
        assert compare("eq", result, "super-secret")

    @pytest.mark.parametrize("resolved", [None, "not-an-ocid"])
    def test_get_invalid_raises_value_error_when_alias_does_not_resolve(
        self, backend: MagicMock, resolved: str | None
    ) -> None:
        """Test an alias resolving to nothing or to a non-OCID is rejected."""
        vault = OciVault(backend=backend, resolve_secret_id=lambda _ref: resolved)

        with pytest.raises(ValueError, match="neither an OCID"):
            vault.get("oci_global_secret_store::db-password")

    def test_get_invalid_raises_value_error_on_alias_without_resolver(
        self, vault: OciVault
    ) -> None:
        """Test aliases are rejected when no resolver is configured."""
        with pytest.raises(ValueError, match="neither an OCID"):
            vault.get("oci_global_secret_store::db-password")

    def test_get_invalid_raises_runtime_error_on_non_json_secret(
        self, vault: OciVault, oci_client: MagicMock
    ) -> None:
        """Test get raises RuntimeError when the secret is not a JSON object."""
        oci_client.get_secret_bundle.return_value = _bundle(b"plain-text")

        with pytest.raises(RuntimeError, match="not valid JSON"):
            vault.get(f"{SECRET_OCID}::db-password")

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
            vault.get(f"{SECRET_OCID}::db-password")

    def test_set_valid_writes_new_version_with_field_replaced(
        self, backend: MagicMock, oci_client: MagicMock
    ) -> None:
        """Test set reads the secret, then writes it back with the field replaced."""
        oci_client.get_secret_bundle.return_value = _bundle(
            b'{"db-password": "old", "other": "x"}'
        )
        resolve = MagicMock(return_value=SECRET_OCID)
        vault = OciVault(backend=backend, resolve_secret_id=resolve)

        vault.set("oci_global_secret_store::db-password", "new")

        oci_client.get_secret_bundle.assert_called_once_with(secret_id=SECRET_OCID)
        vaults_client = backend.get_vaults_client.return_value
        vaults_client.update_secret.assert_called_once()
        kwargs = vaults_client.update_secret.call_args.kwargs
        assert compare("eq", kwargs["secret_id"], SECRET_OCID)
        content = kwargs["update_secret_details"].secret_content
        assert compare("eq", content.content_type, "BASE64")
        assert compare(
            "eq",
            json.loads(base64.b64decode(content.content)),
            {"db-password": "new", "other": "x"},
        )

    def test_set_invalid_raises_runtime_error_on_non_json_secret(
        self, vault: OciVault, backend: MagicMock, oci_client: MagicMock
    ) -> None:
        """Test set refuses to overwrite a secret that is not valid JSON."""
        oci_client.get_secret_bundle.return_value = _bundle(b"plain-text")

        with pytest.raises(RuntimeError, match="not valid JSON"):
            vault.set(f"{SECRET_OCID}::db-password", "new")

        backend.get_vaults_client.return_value.update_secret.assert_not_called()

    def test_set_invalid_raises_value_error_on_alias_without_resolver(
        self, vault: OciVault, backend: MagicMock
    ) -> None:
        """Test set rejects aliases when no resolver is configured."""
        with pytest.raises(ValueError, match="neither an OCID"):
            vault.set("oci_global_secret_store::db-password", "new")

        backend.get_vaults_client.return_value.update_secret.assert_not_called()
