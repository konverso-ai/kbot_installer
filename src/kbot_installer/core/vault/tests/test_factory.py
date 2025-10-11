"""Tests for vault factory functionality."""

import pytest
from unittest.mock import patch, MagicMock

from kbot_installer.core.vault.factory import create_vault
from kbot_installer.core.vault.alias_vault import AliasVault
from kbot_installer.core.vault.azure_vault import AzureVault
from kbot_installer.core.vault.environment_vault import EnvironmentVault


class TestVaultFactory:
    """Test cases for vault factory."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Import all vault classes to ensure they're registered
        from kbot_installer.core.vault.alias_vault import AliasVault
        from kbot_installer.core.vault.azure_vault import AzureVault
        from kbot_installer.core.vault.environment_vault import EnvironmentVault

    @pytest.mark.parametrize("vault_type,expected_name", [
        ("alias", "ALIAS"),
        ("azure", "AZUREKEYVAULT"),
        ("environment", "VARIABLE"),
    ])
    def test_create_vault_creates_correct_type(self, vault_type: str, expected_name: str) -> None:
        """Test that create_vault creates the correct vault type."""
        vault = create_vault(vault_type)
        assert vault.__class__.get_name() == expected_name

    def test_create_vault_alias_without_params(self) -> None:
        """Test creating alias vault without parameters."""
        vault = create_vault("alias")
        assert AliasVault.get_name() == "ALIAS"
        assert vault.get_value("test_key") == "ALIAS"

    @patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential')
    def test_create_vault_azure_with_url(self, mock_credential) -> None:
        """Test creating Azure vault without URL parameter."""
        vault = create_vault("azure")
        assert AzureVault.get_name() == "AZUREKEYVAULT"

    def test_create_vault_environment_with_prefix(self) -> None:
        """Test creating environment vault without prefix parameter."""
        vault = create_vault("environment")
        assert EnvironmentVault.get_name() == "VARIABLE"

    @patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential')
    def test_create_vault_azure_without_url(self, mock_credential) -> None:
        """Test creating Azure vault without URL parameter."""
        vault = create_vault("azure")
        assert AzureVault.get_name() == "AZUREKEYVAULT"

    def test_create_vault_environment_without_prefix(self) -> None:
        """Test creating environment vault without prefix parameter."""
        vault = create_vault("environment")
        assert EnvironmentVault.get_name() == "VARIABLE"

    @pytest.mark.parametrize("vault_type", [
        "alias",
        "azure",
        "environment",
    ])
    def test_create_vault_returns_vault_base_instance(self, vault_type: str) -> None:
        """Test that create_vault returns VaultBase instances."""
        from kbot_installer.core.vault.vault_base import VaultBase
        vault = create_vault(vault_type)
        assert isinstance(vault, VaultBase)

    @patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential')
    def test_create_vault_with_extra_kwargs(self, mock_credential) -> None:
        """Test that create_vault works without extra kwargs."""
        # Azure vault doesn't accept constructor parameters
        vault = create_vault("azure")
        assert AzureVault.get_name() == "AZUREKEYVAULT"

    @patch('kbot_installer.core.vault.factory.factory_method')
    def test_create_vault_calls_factory_method(self, mock_factory_method: MagicMock) -> None:
        """Test that create_vault calls the generic factory_method."""
        mock_vault = MagicMock()
        mock_factory_method.return_value = mock_vault

        result = create_vault("alias")

        mock_factory_method.assert_called_once_with("alias", "kbot_installer.core.vault", **{})
        assert result == mock_vault

    @patch('kbot_installer.core.vault.factory.factory_method')
    def test_create_vault_passes_kwargs_to_factory(self, mock_factory_method: MagicMock) -> None:
        """Test that create_vault passes kwargs to factory_method."""
        mock_vault = MagicMock()
        mock_factory_method.return_value = mock_vault

        result = create_vault("azure", vault_url="https://test.vault.azure.net")

        # Azure vault will receive kwargs but will fail since it doesn't accept them
        expected_kwargs = {"vault_url": "https://test.vault.azure.net"}
        mock_factory_method.assert_called_once_with("azure", "kbot_installer.core.vault", **expected_kwargs)
        assert result == mock_vault

    @patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential')
    def test_create_vault_multiple_instances_independent(self, mock_credential) -> None:
        """Test that multiple vault instances are independent."""
        vault1 = create_vault("azure")
        vault2 = create_vault("azure")

        # Both should have the same name
        assert vault1.__class__.get_name() == vault2.__class__.get_name()

    @pytest.mark.parametrize("vault_type,test_key,expected_value", [
        ("alias", "any_key", "ALIAS"),
        ("azure", "vault::test_key", "secret_value"),
        ("environment", "NONEXISTENT_KEY", ""),
    ])
    def test_created_vaults_work_correctly(self, vault_type: str, test_key: str, expected_value: str | None) -> None:
        """Test that created vaults work correctly with their methods."""
        if vault_type == "azure":
            # Mock Azure vault for testing
            with patch('kbot_installer.core.vault.azure_vault.SecretClient') as mock_client_class, \
                 patch('kbot_installer.core.vault.azure_vault.DefaultAzureCredential'):
                mock_client = MagicMock()
                mock_secret = MagicMock()
                mock_secret.value = expected_value
                mock_client.get_secret.return_value = mock_secret
                mock_client_class.return_value = mock_client

                vault = create_vault(vault_type)
                result = vault.get_value(test_key)
                assert result == expected_value
        else:
            vault = create_vault(vault_type)
            if vault_type == "environment":
                # Environment vault returns empty string for non-existent keys
                result = vault.get_value(test_key)
                assert result == expected_value
            else:
                # Other vaults return their name
                result = vault.get_value(test_key)
                assert result == expected_value
