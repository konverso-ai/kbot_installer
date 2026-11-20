"""Tests for vault base module."""

import pytest

from utils.utils_for_unit_tests import compare
from vault.base import VaultBase


class _DummyVault(VaultBase):
    """Minimal concrete VaultBase used to exercise the abstract interface."""

    def get(self, key: str) -> str:
        """Return a fixed value for the given key, ignoring the vault name."""
        _, key_in_vault = self.parse_key(key)
        return f"value-for-{key_in_vault}"


class TestVaultBase:
    """Test cases for VaultBase abstract class."""

    def test_subclass_valid_implements_get(self) -> None:
        """Test a concrete VaultBase subclass can be instantiated and used."""
        vault = _DummyVault()

        assert compare("eq", vault.get("my-vault::db-password"), "value-for-db-password")


class TestParseKey:
    """Test cases for VaultBase.parse_key static method."""

    def test_parse_key_valid_splits_vault_name_and_key(self) -> None:
        """Test parse_key splits a well-formed key into its two parts."""
        vault_name, key_in_vault = VaultBase.parse_key("my-vault::db-password")

        assert compare("eq", vault_name, "my-vault")
        assert compare("eq", key_in_vault, "db-password")

    def test_parse_key_valid_keeps_further_separators_in_key_part(self) -> None:
        """Test parse_key only splits on the first '::' occurrence."""
        vault_name, key_in_vault = VaultBase.parse_key("my-vault::folder::db-password")

        assert compare("eq", vault_name, "my-vault")
        assert compare("eq", key_in_vault, "folder::db-password")

    @pytest.mark.parametrize(
        "key",
        [
            "no-separator-at-all",
            "::missing-vault-name",
            "missing-key-in-vault::",
            "",
        ],
    )
    def test_parse_key_invalid_raises_value_error(self, key: str) -> None:
        """Test parse_key raises ValueError on malformed keys."""
        with pytest.raises(ValueError, match="Invalid vault key"):
            VaultBase.parse_key(key)
