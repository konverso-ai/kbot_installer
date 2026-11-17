"""AWS Secrets Manager implementation of the secret vault."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from botocore.exceptions import ClientError
from typing_extensions import override

from security.vault.base import VaultBase
from utils.Logger import logger

if TYPE_CHECKING:
    from mypy_boto3_secretsmanager import SecretsManagerClient

    from backend.base import BackendBase

log = logger.get_package_logger("vault")

_NOT_FOUND_CODE = "ResourceNotFoundException"


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

    def _get_client(self) -> SecretsManagerClient:
        """Return the AWS Secrets Manager client from the configured backend.

        Raises:
            RuntimeError: If the backend provides no client.

        """
        client = cast("SecretsManagerClient | None", self._backend.get_client())
        if client is None:
            msg = "Secrets Manager client unavailable. Ensure the S3 backend is configured."
            raise RuntimeError(msg)
        return client

    def _get_content(self, client: SecretsManagerClient, secret_id: str) -> str:
        """Return the raw content of a secret, decoding binary secrets as UTF-8."""
        response = client.get_secret_value(SecretId=secret_id)
        if "SecretString" in response:
            return response["SecretString"]
        return response["SecretBinary"].decode("utf-8")

    @override
    def get(self, key: str) -> str:
        """Retrieve one field of a JSON secret from AWS Secrets Manager.

        Args:
            key: Secret key in the ``<secret-id>::<field>`` form: ``secret-id``
                (name or ARN) identifies the secret, whose content must be a
                JSON object, and ``field`` is the entry of that object to return.

        Returns:
            The field value. The secret content is read from ``SecretBinary``
            (UTF-8) when the secret was stored as binary content.

        Raises:
            ValueError: If ``key`` is not in the ``<secret-id>::<field>`` form.
            RuntimeError: If the Secrets Manager client is unavailable, or if the
                secret is not valid JSON or has no ``field`` entry.
            TypeError: If the secret is valid JSON but not a JSON object.

        """
        secret_id, field = self.parse_key(key)
        content = self._get_content(self._get_client(), secret_id)
        return self.read_json_field(content, field, secret_id)

    @override
    def set(self, key: str, value: str) -> None:
        """Create or replace one field of a JSON secret in AWS Secrets Manager.

        The other fields of the secret are kept. The secret is created, holding
        only ``field``, when it does not exist yet; the updated content is
        always written as ``SecretString``. The read-modify-write is not atomic:
        concurrent writers to the same secret may overwrite each other.

        Args:
            key: Secret key in the ``<secret-id>::<field>`` form: ``secret-id``
                (name or ARN; a name is required to create the secret)
                identifies the secret, whose content must be a JSON object, and
                ``field`` is the entry of that object to set.
            value: Value to store in ``field``.

        Raises:
            ValueError: If ``key`` is not in the ``<secret-id>::<field>`` form.
            RuntimeError: If the Secrets Manager client is unavailable, or if the
                existing secret is not valid JSON.
            TypeError: If the existing secret is valid JSON but not a JSON object.
            ClientError: If AWS Secrets Manager rejects a request.

        """
        secret_id, field = self.parse_key(key)
        client = self._get_client()
        try:
            content = self._get_content(client, secret_id)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != _NOT_FOUND_CODE:
                raise
            client.create_secret(Name=secret_id, SecretString=self.write_json_field(None, field, value, secret_id))
            log.info("Created secret '%s' in AWS Secrets Manager", secret_id)
            return
        client.put_secret_value(
            SecretId=secret_id, SecretString=self.write_json_field(content, field, value, secret_id)
        )
