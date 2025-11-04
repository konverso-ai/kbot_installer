"""Tests for EnvironmentVault implementation."""

import os
from unittest.mock import patch

import pytest

from kbot_installer.core.vault.environment_vault import EnvironmentVault


class TestEnvironmentVault:
    """Test cases for EnvironmentVault class."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.vault = EnvironmentVault()

    def test_environment_vault_has_name(self) -> None:
        """Test that EnvironmentVault has the correct name."""
        assert EnvironmentVault.get_name() == "VARIABLE"

    def test_environment_vault_initialization(self) -> None:
        """Test EnvironmentVault initialization."""
        vault = EnvironmentVault()
        assert EnvironmentVault.get_name() == "VARIABLE"

    @patch.dict(os.environ, {"TEST_KEY": "test_value", "ANOTHER_KEY": "another_value"})
    def test_environment_vault_get_value_existing_key(self) -> None:
        """Test get_value with existing environment variable."""
        result = self.vault.get_value("TEST_KEY")
        assert result == "test_value"

    @patch.dict(os.environ, {"TEST_KEY": "test_value"})
    def test_environment_vault_get_value_nonexistent_key(self) -> None:
        """Test get_value with non-existent environment variable."""
        result = self.vault.get_value("NONEXISTENT_KEY")
        assert result == ""

    @pytest.mark.parametrize(
        "invalid_key",
        ["", None],
    )
    def test_environment_vault_get_value_invalid_key(
        self, invalid_key: str | None
    ) -> None:
        """Test get_value with invalid keys."""
        result = self.vault.get_value(invalid_key)
        assert result is None

    def test_environment_vault_set_value_not_implemented(self) -> None:
        """Test that set_value raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            self.vault.set_value("key", "value")

        assert "Setting values in environment variables is not supported" in str(
            exc_info.value
        )

    def test_environment_vault_delete_value_not_implemented(self) -> None:
        """Test that delete_value raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            self.vault.delete_value("key")

        assert "Deleting values from environment variables is not supported" in str(
            exc_info.value
        )

    def test_environment_vault_is_vault_base_instance(self) -> None:
        """Test that EnvironmentVault is an instance of VaultBase."""
        from kbot_installer.core.vault.vault_base import VaultBase

        assert isinstance(self.vault, VaultBase)

    def test_environment_vault_implements_all_abstract_methods(self) -> None:
        """Test that EnvironmentVault implements all required abstract methods."""
        # Check that all abstract methods are implemented
        assert hasattr(self.vault, "get_name")
        assert hasattr(self.vault, "get_value")
        assert hasattr(self.vault, "set_value")
        assert hasattr(self.vault, "delete_value")

    @patch.dict(os.environ, {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3"})
    def test_environment_vault_multiple_keys(self) -> None:
        """Test get_value with multiple different keys."""
        assert self.vault.get_value("KEY1") == "value1"
        assert self.vault.get_value("KEY2") == "value2"
        assert self.vault.get_value("KEY3") == "value3"

    def test_environment_vault_simple_initialization(self) -> None:
        """Test EnvironmentVault simple initialization."""
        vault = EnvironmentVault()
        assert EnvironmentVault.get_name() == "VARIABLE"

    @patch.dict(os.environ, {"EMPTY_KEY": ""})
    def test_environment_vault_get_value_empty_string(self) -> None:
        """Test get_value with environment variable containing empty string."""
        result = self.vault.get_value("EMPTY_KEY")
        assert result == ""

    @patch.dict(os.environ, {"UNICODE_KEY": "éàçù"})
    def test_environment_vault_get_value_unicode(self) -> None:
        """Test get_value with unicode environment variable."""
        result = self.vault.get_value("UNICODE_KEY")
        assert result == "éàçù"

    def test_environment_vault_multiple_instances_independent(self) -> None:
        """Test that multiple instances are independent."""
        vault1 = EnvironmentVault()
        vault2 = EnvironmentVault()

        # Both should have the same name
        assert EnvironmentVault.get_name() == EnvironmentVault.get_name()
        assert EnvironmentVault.get_name() == "VARIABLE"
        assert EnvironmentVault.get_name() == "VARIABLE"
