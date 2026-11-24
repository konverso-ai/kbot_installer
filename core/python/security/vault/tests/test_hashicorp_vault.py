"""Tests for hashicorp_vault module."""

from unittest.mock import MagicMock

import pytest
from hvac.exceptions import Forbidden

from security.vault.hashicorp_vault import HashicorpVault
from utils.utils_for_unit_tests import compare


@pytest.fixture
def hvac_client() -> MagicMock:
    """Create a mock hvac client returning a KV v2 secret."""
    client = MagicMock()
    client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {
            "data": {"db-password": "super-secret", "port": 5432},
            "metadata": {"version": 3},
        },
    }
    return client


@pytest.fixture
def backend(hvac_client: MagicMock) -> MagicMock:
    """Create a mock HashiCorp Vault backend."""
    mock_backend = MagicMock()
    mock_backend.get_client.return_value = hvac_client
    return mock_backend


@pytest.fixture
def vault(backend: MagicMock) -> HashicorpVault:
    """Create a HashicorpVault instance for testing."""
    return HashicorpVault(backend=backend)


class TestHashicorpVault:
    """Test cases for HashicorpVault class."""

    @pytest.mark.parametrize(
        ("key", "mount_point", "secret_path"),
        [
            ("secret/kbot/global::db-password", "secret", "kbot/global"),
            ("kv/kbot/site-a/db::db-password", "kv", "kbot/site-a/db"),
        ],
    )
    def test_get_valid_returns_field_of_kv_v2_secret(
        self,
        vault: HashicorpVault,
        hvac_client: MagicMock,
        key: str,
        mount_point: str,
        secret_path: str,
    ) -> None:
        """Test get reads the secret at the mount point and returns the requested field."""
        result = vault.get(key)

        hvac_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path=secret_path, mount_point=mount_point, raise_on_deleted_version=True
        )
        assert compare("eq", result, "super-secret")

    def test_get_valid_json_encodes_non_string_values(self, vault: HashicorpVault) -> None:
        """Test get returns non-string field values JSON-encoded."""
        assert compare("eq", vault.get("secret/kbot/global::port"), "5432")

    def test_get_invalid_raises_runtime_error_on_missing_field(self, vault: HashicorpVault) -> None:
        """Test get raises RuntimeError when the secret has no such field."""
        with pytest.raises(RuntimeError, match="'unknown' not found"):
            vault.get("secret/kbot/global::unknown")

    @pytest.mark.parametrize(
        "key",
        ["no-separator", "secret/kbot/global::", "secret::db-password", "secret/::db-password", "/kbot::db-password"],
    )
    def test_get_invalid_raises_value_error_on_malformed_key(
        self, vault: HashicorpVault, hvac_client: MagicMock, key: str
    ) -> None:
        """Test get rejects keys without a mount point, secret path or field."""
        with pytest.raises(ValueError, match="Invalid"):
            vault.get(key)

        hvac_client.secrets.kv.v2.read_secret_version.assert_not_called()

    def test_get_invalid_propagates_vault_errors(self, vault: HashicorpVault, hvac_client: MagicMock) -> None:
        """Test get propagates errors raised by Vault (e.g. a token without access)."""
        hvac_client.secrets.kv.v2.read_secret_version.side_effect = Forbidden("permission denied")

        with pytest.raises(Forbidden):
            vault.get("secret/kbot/site-b::db-password")

    def test_get_invalid_raises_runtime_error_without_client(self) -> None:
        """Test get raises RuntimeError when the backend has no client."""
        backend = MagicMock()
        backend.get_client.return_value = None

        with pytest.raises(RuntimeError, match="HashiCorp Vault client unavailable"):
            HashicorpVault(backend=backend).get("secret/kbot/global::db-password")

    def test_set_invalid_raises_not_implemented(self, vault: HashicorpVault) -> None:
        """Test the vault is read-only."""
        with pytest.raises(NotImplementedError, match="read-only"):
            vault.set("secret/kbot/global::db-password", "new")
