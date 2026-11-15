"""Tests for secret_vault module."""

from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.base import VaultBase
from security.vault.secret_vault import SecretVault


@pytest.fixture
def delegate() -> MagicMock:
    """Create a mock cloud-provider vault."""
    mock_vault = MagicMock(spec=VaultBase)
    mock_vault.get.return_value = "super-secret"
    return mock_vault


class TestSecretVault:
    """Test cases for SecretVault class."""

    def test_get_valid_delegates_key_unchanged_without_expander(self, delegate: MagicMock) -> None:
        """Test get forwards the key as is when no expander is configured."""
        vault = SecretVault(vault=delegate)

        result = vault.get("my-vault::db-password")

        delegate.get.assert_called_once_with("my-vault::db-password")
        assert compare("eq", result, "super-secret")

    def test_get_valid_delegates_expanded_key(self, delegate: MagicMock) -> None:
        """Test get expands the key before delegating."""
        expand = MagicMock(return_value="site-store::db-password")
        vault = SecretVault(vault=delegate, expand=expand)

        result = vault.get("%(site_secret_store)v::db-password")

        expand.assert_called_once_with("%(site_secret_store)v::db-password")
        delegate.get.assert_called_once_with("site-store::db-password")
        assert compare("eq", result, "super-secret")

    def test_get_invalid_propagates_delegate_errors(self, delegate: MagicMock) -> None:
        """Test get propagates errors raised by the underlying vault."""
        delegate.get.side_effect = ValueError("Invalid vault key")
        vault = SecretVault(vault=delegate)

        with pytest.raises(ValueError, match="Invalid vault key"):
            vault.get("no-separator")
