"""Tests for hashicorp_vault_backend module."""

from unittest.mock import patch

import pytest

from backend.hashicorp_vault_backend import HashicorpVaultBackend
from credentials.hashicorp_credentials import HashicorpCredentials
from utils.utils_for_unit_tests import compare


class TestHashicorpVaultBackend:
    """Test cases for HashicorpVaultBackend class."""

    def test_init_valid_builds_client_from_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test HashicorpVaultBackend builds an hvac client from the address and token."""
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.com:8200")
        monkeypatch.setenv("VAULT_TOKEN", "s.token")
        with patch("backend.hashicorp_vault_backend.hvac") as mock_hvac:
            backend = HashicorpVaultBackend(HashicorpCredentials())

            mock_hvac.Client.assert_called_once_with(url="https://vault.example.com:8200", token="s.token")
            assert compare("eq", backend.get_client(), mock_hvac.Client.return_value)

    def test_init_invalid_raises_runtime_error_on_missing_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test HashicorpVaultBackend refuses to build a client without address and token."""
        monkeypatch.delenv("VAULT_ADDR", raising=False)
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
        with (
            patch("backend.hashicorp_vault_backend.hvac") as mock_hvac,
            pytest.raises(RuntimeError, match="VAULT_ADDR, VAULT_TOKEN"),
        ):
            HashicorpVaultBackend(HashicorpCredentials())

        mock_hvac.Client.assert_not_called()
