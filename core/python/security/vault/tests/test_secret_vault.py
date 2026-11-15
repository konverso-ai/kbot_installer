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

    def test_get_valid_delegates_key_unchanged(self, delegate: MagicMock) -> None:
        """Test get forwards the key as is to the underlying vault."""
        vault = SecretVault(vault=delegate)

        result = vault.get("my-vault::db-password")

        delegate.get.assert_called_once_with("my-vault::db-password")
        assert compare("eq", result, "super-secret")

    def test_get_invalid_propagates_delegate_errors(self, delegate: MagicMock) -> None:
        """Test get propagates errors raised by the underlying vault."""
        delegate.get.side_effect = ValueError("Invalid vault key")
        vault = SecretVault(vault=delegate)

        with pytest.raises(ValueError, match="Invalid vault key"):
            vault.get("no-separator")
