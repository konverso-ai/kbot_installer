"""Tests for AliasVault implementation."""

import pytest

from kbot_installer.core.vault.alias_vault import AliasVault


class TestAliasVault:
    """Test cases for AliasVault class."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.vault = AliasVault()

    def test_alias_vault_has_name(self) -> None:
        """Test that AliasVault has the correct name."""
        assert AliasVault.get_name() == "ALIAS"

    @pytest.mark.parametrize("key", [
        "any_key",
        "test_key",
        "key_with_underscores",
        "key-with-dashes",
        "123",
        "special!@#$%",
    ])
    def test_alias_vault_get_value_returns_name(self, key: str) -> None:
        """Test that get_value returns the vault name for any key."""
        result = self.vault.get_value(key)
        assert result == "ALIAS"

    @pytest.mark.parametrize("invalid_key", [
        "",
        None,
    ])
    def test_alias_vault_get_value_with_invalid_key(self, invalid_key: str | None) -> None:
        """Test that get_value returns None for invalid keys."""
        result = self.vault.get_value(invalid_key)
        assert result is None

    @pytest.mark.parametrize("key,value", [
        ("key", "value"),
        ("", "value"),
        ("key", ""),
        ("", ""),
        ("test", "test_value"),
    ])
    def test_alias_vault_set_value_returns_false(self, key: str, value: str) -> None:
        """Test that set_value raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.vault.set_value(key, value)

    @pytest.mark.parametrize("key", [
        "key",
        "",
        "test_key",
        "key_with_underscores",
    ])
    def test_alias_vault_delete_value_returns_false(self, key: str) -> None:
        """Test that delete_value raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.vault.delete_value(key)

    def test_alias_vault_is_vault_base_instance(self) -> None:
        """Test that AliasVault is an instance of VaultBase."""
        from kbot_installer.core.vault.vault_base import VaultBase
        assert isinstance(self.vault, VaultBase)

    def test_alias_vault_implements_all_abstract_methods(self) -> None:
        """Test that AliasVault implements all required abstract methods."""
        # Check that all abstract methods are implemented
        assert hasattr(self.vault, 'get_name')
        assert hasattr(self.vault, 'get_value')
        assert hasattr(self.vault, 'set_value')
        assert hasattr(self.vault, 'delete_value')

    def test_alias_vault_multiple_instances_same_behavior(self) -> None:
        """Test that multiple instances behave the same way."""
        vault1 = AliasVault()
        vault2 = AliasVault()

        # Both should return the same name
        assert AliasVault.get_name() == AliasVault.get_name()

        # Both should return the same value for the same key
        assert vault1.get_value("test") == vault2.get_value("test")

        # Both should raise NotImplementedError for set/delete operations
        with pytest.raises(NotImplementedError):
            vault1.set_value("key", "value")
        with pytest.raises(NotImplementedError):
            vault1.delete_value("key")

    def test_alias_vault_operations_are_stateless(self) -> None:
        """Test that AliasVault operations don't change state."""
        # Get initial value
        initial_value = self.vault.get_value("test_key")

        # Try to set a value (should raise NotImplementedError)
        with pytest.raises(NotImplementedError):
            self.vault.set_value("test_key", "new_value")

        # Try to delete the key (should raise NotImplementedError)
        with pytest.raises(NotImplementedError):
            self.vault.delete_value("test_key")

        # Value should still be the same
        final_value = self.vault.get_value("test_key")
        assert initial_value == final_value == "ALIAS"
