"""Tests for azure_vault module."""

from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.azure_vault import AzureVault


@pytest.fixture
def clients() -> dict[str, MagicMock]:
    """Map each Key Vault name to its own mock SecretClient."""
    return {}


@pytest.fixture
def backend_factory(clients: dict[str, MagicMock]) -> MagicMock:
    """Create a backend factory returning one mock backend per Key Vault name."""

    def build(vault_name: str) -> MagicMock:
        backend = MagicMock()
        backend.get_client.return_value = clients.setdefault(vault_name, MagicMock())
        return backend

    return MagicMock(side_effect=build)


@pytest.fixture
def vault(backend_factory: MagicMock) -> AzureVault:
    """Create an AzureVault instance for testing."""
    return AzureVault(backend_factory=backend_factory)


class TestAzureVault:
    """Test cases for AzureVault class."""

    def test_get_valid_returns_secret_value(
        self, vault: AzureVault, clients: dict[str, MagicMock]
    ) -> None:
        """Test get reads the secret from the Key Vault named in the key."""
        clients["my-vault"] = MagicMock()
        clients["my-vault"].get_secret.return_value.value = "super-secret"

        result = vault.get("my-vault::db-password")

        clients["my-vault"].get_secret.assert_called_once_with("db-password")
        assert compare("eq", result, "super-secret")

    def test_get_valid_routes_each_key_to_its_own_key_vault(
        self, vault: AzureVault, clients: dict[str, MagicMock]
    ) -> None:
        """Test keys naming different Key Vaults reach different clients."""
        clients["vault-a"] = MagicMock()
        clients["vault-a"].get_secret.return_value.value = "a-secret"
        clients["vault-b"] = MagicMock()
        clients["vault-b"].get_secret.return_value.value = "b-secret"

        assert compare("eq", vault.get("vault-a::s"), "a-secret")
        assert compare("eq", vault.get("vault-b::s"), "b-secret")

    def test_get_valid_builds_one_backend_per_key_vault(
        self, vault: AzureVault, backend_factory: MagicMock
    ) -> None:
        """Test the backend of a Key Vault is built once and then reused."""
        vault.get("vault-a::one")
        vault.get("vault-a::two")
        vault.get("vault-b::one")

        assert compare("eq", backend_factory.call_count, 2)

    def test_get_invalid_raises_value_error_on_malformed_key(
        self, vault: AzureVault
    ) -> None:
        """Test get propagates ValueError for a malformed key."""
        with pytest.raises(ValueError, match="Invalid vault key"):
            vault.get("no-separator")

    def test_get_invalid_raises_runtime_error_without_client(self) -> None:
        """Test get raises RuntimeError when the backend has no client."""
        backend = MagicMock()
        backend.get_client.return_value = None
        vault = AzureVault(backend_factory=lambda _name: backend)

        with pytest.raises(RuntimeError, match="Azure Key Vault client unavailable"):
            vault.get("my-vault::db-password")

    def test_get_invalid_raises_runtime_error_when_secret_has_no_value(
        self, vault: AzureVault, clients: dict[str, MagicMock]
    ) -> None:
        """Test get raises RuntimeError when the retrieved secret has no value."""
        clients["my-vault"] = MagicMock()
        clients["my-vault"].get_secret.return_value.value = None

        with pytest.raises(RuntimeError, match="has no value"):
            vault.get("my-vault::db-password")

    def test_set_valid_stores_secret_in_named_key_vault(
        self, vault: AzureVault, clients: dict[str, MagicMock]
    ) -> None:
        """Test set writes the secret into the Key Vault named in the key."""
        clients["my-vault"] = MagicMock()

        vault.set("my-vault::token", "value")

        clients["my-vault"].set_secret.assert_called_once_with("token", "value")

    def test_set_invalid_raises_value_error_on_malformed_key(
        self, vault: AzureVault
    ) -> None:
        """Test set propagates ValueError for a malformed key."""
        with pytest.raises(ValueError, match="Invalid vault key"):
            vault.set("no-separator", "value")
