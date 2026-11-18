"""Tests for vault base module."""

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.base import VaultBase


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

    def test_set_invalid_is_read_only_by_default(self) -> None:
        """Test vaults that do not override set reject writes."""
        with pytest.raises(NotImplementedError, match="_DummyVault is read-only"):
            _DummyVault().set("my-vault::db-password", "value")


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


class TestReadJsonField:
    """Test cases for VaultBase.read_json_field static method."""

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            ('{"field": "text"}', "text"),
            ('{"field": 5432}', "5432"),
            ('{"field": true}', "true"),
            ('{"field": {"nested": 1}}', '{"nested": 1}'),
        ],
    )
    def test_read_json_field_valid_returns_field_as_string(
        self, content: str, expected: str
    ) -> None:
        """Test string fields are returned as is and others JSON-encoded."""
        result = VaultBase.read_json_field(content, "field", "my-secret")

        assert compare("eq", result, expected)

    @pytest.mark.parametrize(
        ("content", "error", "match"),
        [
            ("not json", RuntimeError, "is not valid JSON"),
            ('["field"]', TypeError, "must be a JSON object"),
            ('{"other": "x"}', RuntimeError, "Field 'field' not found in secret 'my-secret'"),
        ],
    )
    def test_read_json_field_invalid_raises(
        self, content: str, error: type[Exception], match: str
    ) -> None:
        """Test invalid JSON, non-object content and missing fields are rejected."""
        with pytest.raises(error, match=match):
            VaultBase.read_json_field(content, "field", "my-secret")
