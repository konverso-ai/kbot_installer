"""Oracle Cloud Infrastructure (OCI) Vault implementation of the secret vault."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, cast

from oci.vault.models import Base64SecretContentDetails, UpdateSecretDetails
from typing_extensions import override

from security.vault.base import VaultBase
from utils.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from oci.secrets import SecretsClient

    from backend.oci_vault_backend import OciVaultBackend

log = logger.get_package_logger("vault")

_OCID_PREFIX = "ocid1."


class OciVault(VaultBase):
    """``VaultBase`` implementation backed by OCI Vault secrets."""

    _backend: OciVaultBackend
    _resolve_secret_id: Callable[[str], str | None] | None

    def __init__(
        self,
        backend: OciVaultBackend,
        resolve_secret_id: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize the OCI vault.

        Args:
            backend: Pre-configured OCI Vault backend used to reach OCI Vault
                secrets. Building the backend (and its credentials) is not
                this class's responsibility.
            resolve_secret_id: Function mapping a secret alias that is not an
                OCID to the secret OCID (e.g. kbot's ``Settings().GetConfig``,
                for settings such as ``oci_global_secret_store``), or None when
                undefined. If None, only OCIDs are accepted.

        """
        self._backend = backend
        self._resolve_secret_id = resolve_secret_id

    def _get_client(self) -> SecretsClient:
        """Return the OCI Secrets client from the configured backend.

        Raises:
            RuntimeError: If the backend provides no client.

        """
        client = cast("SecretsClient | None", self._backend.get_client())
        if client is None:
            msg = "OCI Secrets client unavailable. Ensure the OCI backend is configured."
            raise RuntimeError(msg)
        return client

    def _get_secret_ocid(self, secret_ref: str) -> str:
        """Return the OCID of a secret given its OCID or its alias.

        Args:
            secret_ref: Secret OCID, or alias resolved via ``resolve_secret_id``.

        Returns:
            The secret OCID.

        Raises:
            ValueError: If ``secret_ref`` is neither an OCID nor an alias
                resolving to one.

        """
        if secret_ref.startswith(_OCID_PREFIX):
            return secret_ref
        if self._resolve_secret_id is not None:
            resolved = self._resolve_secret_id(secret_ref)
            if resolved and resolved.startswith(_OCID_PREFIX):
                return resolved
        msg = f"Secret {secret_ref!r} is neither an OCID nor an alias resolving to one"
        raise ValueError(msg)

    def _get_content(self, secret_id: str) -> str:
        """Return the decoded content of the current version of a secret."""
        response = self._get_client().get_secret_bundle(secret_id=secret_id)
        content = response.data.secret_bundle_content.content
        return base64.b64decode(content).decode("utf-8")

    @override
    def get(self, key: str) -> str:
        """Retrieve one field of a JSON secret from OCI Vault.

        Args:
            key: Secret key in the ``<secret>::<field>`` form: ``secret`` is the
                secret OCID or an alias resolved via ``resolve_secret_id``; the
                secret content must be a JSON object, and ``field`` is the entry
                of that object to return.

        Returns:
            The field value.

        Raises:
            ValueError: If ``key`` is not in the ``<secret>::<field>`` form, or
                if ``secret`` does not resolve to an OCID.
            RuntimeError: If the OCI Secrets client is unavailable, or if the
                secret is not valid JSON or has no ``field`` entry.
            TypeError: If the secret is valid JSON but not a JSON object.

        """
        secret_ref, field = self.parse_key(key)
        content = self._get_content(self._get_secret_ocid(secret_ref))
        return self.read_json_field(content, field, secret_ref)

    @override
    def set(self, key: str, value: str) -> None:
        """Create or replace one field of a JSON secret in OCI Vault.

        Writes a new version of the secret, keeping its other fields. The secret
        must already exist: creating one needs a compartment, vault and
        encryption key that the key form does not carry. The read-modify-write
        is not atomic: concurrent writers to the same secret may overwrite each
        other.

        Args:
            key: Secret key in the ``<secret>::<field>`` form: ``secret`` is the
                secret OCID or an alias resolved via ``resolve_secret_id``; the
                secret content must be a JSON object, and ``field`` is the entry
                of that object to set.
            value: Value to store in ``field``.

        Raises:
            ValueError: If ``key`` is not in the ``<secret>::<field>`` form, or
                if ``secret`` does not resolve to an OCID.
            RuntimeError: If an OCI client is unavailable, or if the secret is
                not valid JSON.
            TypeError: If the secret is valid JSON but not a JSON object.
            oci.exceptions.ServiceError: If OCI rejects a request (e.g. the
                secret does not exist).

        """
        secret_ref, field = self.parse_key(key)
        secret_id = self._get_secret_ocid(secret_ref)
        content = self.write_json_field(self._get_content(secret_id), field, value, secret_ref)
        details = UpdateSecretDetails(
            secret_content=Base64SecretContentDetails(
                content_type=Base64SecretContentDetails.CONTENT_TYPE_BASE64,
                content=base64.b64encode(content.encode("utf-8")).decode("ascii"),
            ),
        )
        self._backend.get_vaults_client().update_secret(secret_id=secret_id, update_secret_details=details)
