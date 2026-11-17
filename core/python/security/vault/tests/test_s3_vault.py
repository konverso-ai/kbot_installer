"""Tests for s3_vault module."""

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from utils.utils_for_unit_tests import compare
from security.vault.s3_vault import S3Vault


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

    def test_get_valid_returns_json_field_of_secret_string(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test get reads the secret named first and returns the field named second."""
        secretsmanager_client.get_secret_value.return_value = {
            "SecretString": '{"db-password": "super-secret", "other": "x"}',
        }

        result = vault.get("prod/db::db-password")

        secretsmanager_client.get_secret_value.assert_called_once_with(
            SecretId="prod/db"
        )
        assert compare("eq", result, "super-secret")

    def test_get_valid_decodes_secret_binary(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test get decodes SecretBinary content when SecretString is absent."""
        secretsmanager_client.get_secret_value.return_value = {
            "SecretBinary": b'{"db-password": "super-secret"}',
        }

        result = vault.get("prod/db::db-password")

        assert compare("eq", result, "super-secret")

    def test_get_invalid_raises_runtime_error_on_missing_field(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test get raises RuntimeError when the secret lacks the requested field."""
        secretsmanager_client.get_secret_value.return_value = {
            "SecretString": '{"other": "x"}',
        }

        with pytest.raises(RuntimeError, match="not found in secret"):
            vault.get("prod/db::db-password")

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
            vault.get("prod/db::db-password")

    def test_set_valid_updates_field_and_keeps_others(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test set rewrites the secret with the field replaced and others kept."""
        secretsmanager_client.get_secret_value.return_value = {
            "SecretString": '{"db-password": "old", "other": "x"}',
        }

        vault.set("prod/db::db-password", "new")

        secretsmanager_client.put_secret_value.assert_called_once()
        kwargs = secretsmanager_client.put_secret_value.call_args.kwargs
        assert compare("eq", kwargs["SecretId"], "prod/db")
        assert compare(
            "eq", json.loads(kwargs["SecretString"]), {"db-password": "new", "other": "x"}
        )
        secretsmanager_client.create_secret.assert_not_called()

    def test_set_valid_creates_missing_secret(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test set creates the secret holding only the field when it does not exist."""
        secretsmanager_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
        )

        vault.set("prod/db::db-password", "new")

        kwargs = secretsmanager_client.create_secret.call_args.kwargs
        assert compare("eq", kwargs["Name"], "prod/db")
        assert compare("eq", json.loads(kwargs["SecretString"]), {"db-password": "new"})
        secretsmanager_client.put_secret_value.assert_not_called()

    def test_set_invalid_propagates_other_client_errors(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test set does not create the secret on errors other than not-found."""
        secretsmanager_client.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException"}}, "GetSecretValue"
        )

        with pytest.raises(ClientError):
            vault.set("prod/db::db-password", "new")

        secretsmanager_client.create_secret.assert_not_called()
        secretsmanager_client.put_secret_value.assert_not_called()

    def test_set_invalid_raises_type_error_on_non_object_secret(
        self, vault: S3Vault, secretsmanager_client: MagicMock
    ) -> None:
        """Test set refuses to overwrite a secret that is not a JSON object."""
        secretsmanager_client.get_secret_value.return_value = {"SecretString": "[1]"}

        with pytest.raises(TypeError, match="must be a JSON object"):
            vault.set("prod/db::db-password", "new")

        secretsmanager_client.put_secret_value.assert_not_called()
