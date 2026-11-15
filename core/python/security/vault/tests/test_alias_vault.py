"""Tests for alias_vault module."""

from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.alias_vault import AliasVault


class TestAliasVault:
    """Test cases for AliasVault class."""

    def test_get_valid_returns_target_setting_value(self) -> None:
        """Test get expands the key, then returns the value of the setting it names."""
        expand = MagicMock(return_value="db_password_prod")
        get_config = MagicMock(return_value="super-secret")
        vault = AliasVault(get_config=get_config, expand=expand)

        result = vault.get("db_password_%(env)v")

        expand.assert_called_once_with("db_password_%(env)v")
        get_config.assert_called_once_with("db_password_prod")
        assert compare("eq", result, "super-secret")

    def test_get_valid_returns_empty_target_value(self) -> None:
        """Test get returns an empty string target value instead of raising."""
        vault = AliasVault(get_config=MagicMock(return_value=""), expand=lambda key: key)

        assert compare("eq", vault.get("empty_setting"), "")

    def test_get_invalid_raises_runtime_error_when_target_undefined(self) -> None:
        """Test get raises RuntimeError when the target setting is undefined."""
        vault = AliasVault(get_config=MagicMock(return_value=None), expand=lambda key: key)

        with pytest.raises(RuntimeError, match="'missing_setting' is not defined"):
            vault.get("missing_setting")
