"""Tests for s3_vault module."""

from unittest.mock import MagicMock

import pytest

from utils.utils_for_unit_tests import compare
from vault.s3_vault import S3Vault


@pytest.fixture
def secretsmanager_client() -> MagicMock:
    """Create a mock AWS Secrets Manager client."""
    return MagicMock()


@pytest.fixture
def backend(secretsmanager_client: MagicMock) -> MagicMock:
    """Create a mock S3 Vault backend."""
    mock_backend = MagicMock()
    mock_backend.get_client.return_value = secretsmanager_client
    return mock_backend


@pytest.fixture
def vault(backend: MagicMock) -> S3Vault:
    """Create an S3Vault instance for testing."""
    return S3Vault(backend=backend)


class TestS3Vault:
    """Test cases for S3Vault class."""

    def test_get_valid_returns_secret_string(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test get calls get_secret_value and returns the SecretString."""
        secretsmanager_client.get_secret_value.return_value = {
            "SecretString": "super-secret",
        }

        result = vault.get("my-vault::db-password")

        secretsmanager_client.get_secret_value.assert_called_once_with(
            SecretId="db-password"
        )
        assert compare("eq", result, "super-secret")

    def test_get_valid_decodes_secret_binary(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test get decodes SecretBinary content when SecretString is absent."""
        secretsmanager_client.get_secret_value.return_value = {
            "SecretBinary": b"super-secret",
        }

        result = vault.get("my-vault::db-password")

        assert compare("eq", result, "super-secret")

    def test_get_invalid_raises_value_error_on_malformed_key(
        self, vault: S3Vault
    ) -> None:
        """Test get propagates ValueError for a malformed key."""
        with pytest.raises(ValueError, match="Invalid vault key"):
            vault.get("no-separator")

    def test_get_invalid_raises_runtime_error_without_client(self) -> None:
        """Test get raises RuntimeError when the backend has no client."""
        backend = MagicMock()
        backend.get_client.return_value = None
        vault = S3Vault(backend=backend)

        with pytest.raises(RuntimeError, match="Secrets Manager client unavailable"):
            vault.get("my-vault::db-password")
