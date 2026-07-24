"""AWS Secrets Manager implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from typing_extensions import override

from utils.Logger import logger
from vault.base import VaultBase

if TYPE_CHECKING:
    from mypy_boto3_secretsmanager import SecretsManagerClient

    from backend.base import BackendBase

log = logger.get_package_logger("vault")


class S3Vault(VaultBase):
    """``VaultBase`` implementation backed by AWS Secrets Manager."""

    _backend: BackendBase

    def __init__(self, backend: BackendBase) -> None:
        """Initialize the S3 vault.

        Args:
            backend: Pre-configured AWS Secrets Manager backend used to reach
                AWS Secrets Manager. Building the backend (and its
                credentials) is not this class's responsibility.

        """
        self._backend = backend

    def _get_client(self) -> SecretsManagerClient | None:
        """Return the AWS Secrets Manager client from the configured backend."""
        return cast("SecretsManagerClient | None", self._backend.get_client())

    @override
    def get(self, key: str) -> str:
        """Retrieve a secret value from AWS Secrets Manager.

        Args:
            key: Secret key in the ``<vault-name>::<key-in-vault>`` form. AWS
                Secrets Manager has no notion of named vaults, so the vault
                name segment is not used; ``key-in-vault`` is used directly as
                the secret id (name or ARN).

        Returns:
            The secret value, decoded from ``SecretBinary`` when the secret
            was stored as binary content.

        Raises:
            ValueError: If ``key`` is not in the ``<vault-name>::<key-in-vault>`` form.
            RuntimeError: If the Secrets Manager client is unavailable.

        """
        _, secret_name = self.parse_key(key)
        client = self._get_client()
        if client is None:
            msg = (
                "Secrets Manager client unavailable. Ensure the S3 backend "
                "is configured."
            )
            raise RuntimeError(msg)

        response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in response:
            return response["SecretString"]
        return response["SecretBinary"].decode("utf-8")
