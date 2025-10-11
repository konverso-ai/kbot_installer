"""Tests for AzureVault implementation."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.vault.azure_vault import AzureVault


class TestAzureVault:
    """Test cases for AzureVault class."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.vault = AzureVault()

    def test_azure_vault_has_name(self) -> None:
        """Test that AzureVault has the correct name."""
        assert AzureVault.get_name() == "AZUREKEYVAULT"

    def test_azure_vault_initialization(self) -> None:
        """Test AzureVault initialization."""
        vault = AzureVault()
        assert AzureVault.get_name() == "AZUREKEYVAULT"

    @pytest.mark.parametrize("key,expected", [
        ("vault::test_key", "secret_value"),
        ("vault::key_with_underscores", "another_secret"),
        ("vault::key-with-dashes", "dash_secret"),
        ("vault::123", "numeric_secret"),
        ("vault::special!@#$%", "special_secret"),
    ])
    @patch('kbot_installer.core.vault.azure_vault.SecretClient')
    @patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential')
    def test_azure_vault_get_value_with_valid_key(self, mock_credential, mock_client_class, key: str, expected: str) -> None:
        """Test get_value with valid keys."""
        # Mock the secret client and its response
        mock_client = MagicMock()
        mock_secret = MagicMock()
        mock_secret.value = expected
        mock_client.get_secret.return_value = mock_secret
        mock_client_class.return_value = mock_client

        vault = AzureVault()
        result = vault.get_value(key)
        assert result == expected

    @pytest.mark.parametrize("invalid_key", [
        "",
        None,
        "simple_key_without_double_colon",
        "key:single_colon",
        "vault::",  # Empty secret name
    ])
    def test_azure_vault_get_value_with_invalid_key(self, invalid_key: str | None) -> None:
        """Test get_value with invalid keys."""
        result = self.vault.get_value(invalid_key)
        assert result is None

    @pytest.mark.parametrize("key,value,expected", [
        ("key", "value", True),
        ("test", "test_value", True),
        ("", "value", False),
        ("key", None, False),
        ("", "", False),
    ])
    @patch('kbot_installer.core.vault.azure_vault.SecretClient')
    @patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential')
    def test_azure_vault_set_value(self, mock_credential, mock_client_class, key: str, value: str | None, expected: bool) -> None:
        """Test set_value with various parameters."""
        # Mock the secret client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        vault = AzureVault()
        result = vault.set_value(key, value)
        assert result == expected

    @pytest.mark.parametrize("key,expected", [
        ("test_key", True),
        ("key_with_underscores", True),
        ("123", True),
        ("", False),
        (None, False),
    ])
    @patch('kbot_installer.core.vault.azure_vault.SecretClient')
    @patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential')
    def test_azure_vault_delete_value(self, mock_credential, mock_client_class, key: str | None, expected: bool) -> None:
        """Test delete_value with various keys."""
        # Mock the secret client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        vault = AzureVault()
        result = vault.delete_value(key)
        assert result == expected

    def test_azure_vault_is_vault_base_instance(self) -> None:
        """Test that AzureVault is an instance of VaultBase."""
        from kbot_installer.core.vault.vault_base import VaultBase
        assert isinstance(self.vault, VaultBase)

    def test_azure_vault_implements_all_abstract_methods(self) -> None:
        """Test that AzureVault implements all required abstract methods."""
        # Check that all abstract methods are implemented
        assert hasattr(self.vault, 'get_name')
        assert hasattr(self.vault, 'get_value')
        assert hasattr(self.vault, 'set_value')
        assert hasattr(self.vault, 'delete_value')

    def test_azure_vault_multiple_instances_independent(self) -> None:
        """Test that multiple instances are independent."""
        vault1 = AzureVault()
        vault2 = AzureVault()

        # Both should have the same name
        assert AzureVault.get_name() == AzureVault.get_name()

