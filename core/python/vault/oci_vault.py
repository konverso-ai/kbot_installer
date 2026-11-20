"""Oracle Cloud Infrastructure (OCI) Vault implementation of the secret vault."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, cast

from typing_extensions import override

from utils.Logger import logger
from vault.base import VaultBase

if TYPE_CHECKING:
    from oci.secrets import SecretsClient

    from backend.base import BackendBase

log = logger.get_package_logger("vault")


class OciVault(VaultBase):
    """``VaultBase`` implementation backed by OCI Vault secrets."""

    _backend: BackendBase

    def __init__(self, backend: BackendBase) -> None:
        """Initialize the OCI vault.

        Args:
            backend: Pre-configured OCI Vault backend used to reach OCI Vault
                secrets. Building the backend (and its credentials) is not
                this class's responsibility.

        """
        self._backend = backend

    def _get_client(self) -> SecretsClient | None:
        """Return the OCI Secrets client from the configured backend."""
        return cast("SecretsClient | None", self._backend.get_client())

    @override
    def get(self, key: str) -> str:
        """Retrieve a secret value from OCI Vault.

        Args:
            key: Secret key in the ``<vault-name>::<key-in-vault>`` form. The
                vault name segment is used as the OCI vault OCID
                (``vault_id``), required by the OCI Secrets API alongside the
                secret name.

        Returns:
            The decoded secret value.

        Raises:
            ValueError: If ``key`` is not in the ``<vault-name>::<key-in-vault>`` form.
            RuntimeError: If the OCI Secrets client is unavailable.

        """
        vault_id, secret_name = self.parse_key(key)
        client = self._get_client()
        if client is None:
            msg = "OCI Secrets client unavailable. Ensure the OCI backend is configured."
            raise RuntimeError(msg)

        response = client.get_secret_bundle_by_name(
            secret_name=secret_name, vault_id=vault_id
        )
        content = response.data.secret_bundle_content.content
        return base64.b64decode(content).decode("utf-8")
