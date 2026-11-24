"""HashiCorp Vault implementation of the secret vault."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from typing_extensions import override

from security.vault.base import VaultBase

if TYPE_CHECKING:
    import hvac

    from backend.base import BackendBase


class HashicorpVault(VaultBase):
    """``VaultBase`` implementation backed by a HashiCorp Vault KV v2 secrets engine."""

    _backend: BackendBase

    def __init__(self, backend: BackendBase) -> None:
        """Initialize the HashiCorp vault.

        Args:
            backend: Pre-configured HashiCorp Vault backend used to reach the
                Vault server. Building the backend (and its credentials) is not
                this class's responsibility.

        """
        self._backend = backend

    def _get_client(self) -> hvac.Client:
        """Return the HashiCorp Vault client from the configured backend.

        Raises:
            RuntimeError: If the backend provides no client.

        """
        client = cast("hvac.Client | None", self._backend.get_client())
        if client is None:
            msg = "HashiCorp Vault client unavailable. Ensure the HashiCorp backend is configured."
            raise RuntimeError(msg)
        return client

    @override
    def get(self, key: str) -> str:
        """Retrieve one field of a KV v2 secret from HashiCorp Vault.

        Args:
            key: Secret key in the ``<mount>/<secret-path>::<field>`` form:
                ``mount`` is the KV v2 secrets engine mount point (e.g.
                ``secret``), ``secret-path`` the secret inside it (e.g.
                ``kbot/global``), and ``field`` the entry of that secret to return.

        Returns:
            The field value; non-string values are returned JSON-encoded.

        Raises:
            ValueError: If ``key`` is not in the ``<mount>/<secret-path>::<field>`` form.
            RuntimeError: If the HashiCorp Vault client is unavailable, or if the
                secret has no ``field`` entry.
            hvac.exceptions.VaultError: If Vault rejects the request (e.g. the
                secret does not exist, or the token cannot read it).

        """
        path, field = self.parse_key(key)
        mount_point, _, secret_path = path.partition("/")
        if not mount_point or not secret_path:
            msg = f"Invalid HashiCorp Vault key {key!r}, expected '<mount>/<secret-path>::<field>'"
            raise ValueError(msg)
        response = self._get_client().secrets.kv.v2.read_secret_version(
            path=secret_path,
            mount_point=mount_point,
            raise_on_deleted_version=True,
        )
        data = response["data"]["data"]
        if field not in data:
            msg = f"Field {field!r} not found in secret {path!r}"
            raise RuntimeError(msg)
        value = data[field]
        return value if isinstance(value, str) else json.dumps(value)
