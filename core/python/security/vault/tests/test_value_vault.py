"""Tests for value_vault module."""

from unittest.mock import MagicMock

from utils.utils_for_unit_tests import compare
from security.vault.value_vault import ValueVault


class TestValueVault:
    """Test cases for ValueVault class."""

    def test_get_valid_returns_expanded_key(self) -> None:
        """Test get returns the key expanded by the injected expander."""
        expand = MagicMock(return_value="https://bot.example.com/api")
        vault = ValueVault(expand=expand)

        result = vault.get("%(server_url)v/api")

        expand.assert_called_once_with("%(server_url)v/api")
        assert compare("eq", result, "https://bot.example.com/api")
