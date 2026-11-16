"""Tests for value_vault module."""

from utils.utils_for_unit_tests import compare
from security.vault.value_vault import ValueVault


class TestValueVault:
    """Test cases for ValueVault class."""

    def test_get_valid_returns_key(self) -> None:
        """Test get returns the key unchanged (settings references are expanded by the caller)."""
        assert compare("eq", ValueVault().get("https://bot.example.com/api"), "https://bot.example.com/api")
