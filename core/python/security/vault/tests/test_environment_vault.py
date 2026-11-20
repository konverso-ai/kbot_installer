"""Tests for environment_vault module."""

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.environment_vault import EnvironmentVault


class TestEnvironmentVault:
    """Test cases for EnvironmentVault class."""

    def test_get_valid_returns_environment_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get returns the environment variable value."""
        monkeypatch.setenv("KBOT_TEST_SECRET", "super-secret")

        assert compare("eq", EnvironmentVault().get("KBOT_TEST_SECRET"), "super-secret")

    def test_get_valid_keeps_key_with_separator_as_is(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get does not parse '::' as a vault-name separator."""
        monkeypatch.setenv("A::B", "value")

        assert compare("eq", EnvironmentVault().get("A::B"), "value")

    def test_get_invalid_raises_runtime_error_when_undefined(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test get raises RuntimeError for an undefined environment variable."""
        monkeypatch.delenv("KBOT_TEST_SECRET", raising=False)

        with pytest.raises(RuntimeError, match="'KBOT_TEST_SECRET' is not defined"):
            EnvironmentVault().get("KBOT_TEST_SECRET")
