"""Tests for azure_vault module."""

from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from vault.azure_vault import AzureVault


@pytest.fixture
def secret_client() -> MagicMock:
    """Create a mock Azure Key Vault SecretClient."""
    return MagicMock()


@pytest.fixture
def backend(secret_client: MagicMock) -> MagicMock:
    """Create a mock Azure Vault backend."""
    mock_backend = MagicMock()
    mock_backend.get_client.return_value = secret_client
    return mock_backend


@pytest.fixture
def vault(backend: MagicMock) -> AzureVault:
    """Create an AzureVault instance for testing."""
    return AzureVault(backend=backend)


class TestAzureVault:
    """Test cases for AzureVault class."""

    def test_get_valid_returns_secret_value(
        self, vault: AzureVault, secret_client: MagicMock
    ) -> None:
        """Test get calls get_secret and returns its value."""
        mock_secret = MagicMock()
        mock_secret.value = "super-secret"
        secret_client.get_secret.return_value = mock_secret

        result = vault.get("my-vault::db-password")

        secret_client.get_secret.assert_called_once_with("db-password")
        assert compare("eq", result, "super-secret")

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
        vault = AzureVault(backend=backend)

        with pytest.raises(RuntimeError, match="Azure Key Vault client unavailable"):
            vault.get("my-vault::db-password")

    def test_get_invalid_raises_runtime_error_when_secret_has_no_value(
        self, vault: AzureVault, secret_client: MagicMock
    ) -> None:
        """Test get raises RuntimeError when the retrieved secret has no value."""
        mock_secret = MagicMock()
        mock_secret.value = None
        secret_client.get_secret.return_value = mock_secret

        with pytest.raises(RuntimeError, match="has no value"):
            vault.get("my-vault::db-password")
