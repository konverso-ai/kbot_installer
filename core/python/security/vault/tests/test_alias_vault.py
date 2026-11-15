"""Tests for alias_vault module."""

from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.alias_vault import AliasVault


class TestAliasVault:
    """Test cases for AliasVault class."""

    def test_get_valid_returns_target_setting_value(self) -> None:
        """Test get returns the value of the setting the key names."""
        get_config = MagicMock(return_value="super-secret")
        vault = AliasVault(get_config=get_config)

        result = vault.get("db_password_prod")

        get_config.assert_called_once_with("db_password_prod")
        assert compare("eq", result, "super-secret")

    def test_get_valid_returns_empty_target_value(self) -> None:
        """Test get returns an empty string target value instead of raising."""
        vault = AliasVault(get_config=MagicMock(return_value=""))

        assert compare("eq", vault.get("empty_setting"), "")

    def test_get_invalid_raises_runtime_error_when_target_undefined(self) -> None:
        """Test get raises RuntimeError when the target setting is undefined."""
        vault = AliasVault(get_config=MagicMock(return_value=None))

        with pytest.raises(RuntimeError, match="'missing_setting' is not defined"):
            vault.get("missing_setting")
