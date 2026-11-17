"""Secret vault abstractions."""

import json
from abc import ABC, abstractmethod
from typing import cast


class VaultBase(ABC):
    """Abstract base class for secret vault operations."""

    @abstractmethod
    def get(self, key: str) -> str:
        """Retrieve a secret value from the vault.

        Args:
            key: Secret key. Cloud-provider vaults expect the
                ``<vault-name>::<key-in-vault>`` form (see ``parse_key``); other
                vaults document their own key format.

        Returns:
            The secret value.

        Raises:
            ValueError: If ``key`` is malformed for this vault.

        """

    def set(self, key: str, value: str) -> None:
        """Store a secret value in the vault, creating or replacing it.

        Vaults are read-only unless they override this method.

        Args:
            key: Secret key, in the same form as accepted by ``get``.
            value: Secret value to store.

        Raises:
            NotImplementedError: If the vault does not support writes.

        """
        msg = f"{type(self).__name__} is read-only"
        raise NotImplementedError(msg)

    @staticmethod
    def parse_key(key: str) -> tuple[str, str]:
        """Split a vault key into its vault name and in-vault key parts.

        Args:
            key: Secret key in the ``<vault-name>::<key-in-vault>`` form.

        Returns:
            A ``(vault_name, key_in_vault)`` tuple.

        Raises:
            ValueError: If ``key`` does not contain the ``::`` separator, or if
                either the vault name or the in-vault key part is empty.

        """
        vault_name, separator, key_in_vault = key.partition("::")
        if not separator or not vault_name or not key_in_vault:
            msg = f"Invalid vault key {key!r}, expected '<vault-name>::<key-in-vault>'"
            raise ValueError(msg)
        return vault_name, key_in_vault

    @staticmethod
    def read_json_field(content: str, field: str, secret_id: str) -> str:
        """Extract one field from a secret whose content is a JSON object.

        Args:
            content: Raw secret content.
            field: Name of the top-level field to return.
            secret_id: Secret identifier, used in error messages only.

        Returns:
            The field value; non-string values are returned JSON-encoded.

        Raises:
            RuntimeError: If ``content`` is not valid JSON, or if it has no
                ``field`` entry.
            TypeError: If ``content`` is valid JSON but not a JSON object.

        """
        data = VaultBase._load_json_object(content, secret_id)
        if field not in data:
            msg = f"Field {field!r} not found in secret {secret_id!r}"
            raise RuntimeError(msg)
        value = data[field]
        return value if isinstance(value, str) else json.dumps(value)

    @staticmethod
    def write_json_field(content: str | None, field: str, value: str, secret_id: str) -> str:
        """Set one field of a secret whose content is a JSON object.

        Args:
            content: Raw secret content, or None to start from an empty object.
            field: Name of the top-level field to create or replace.
            value: Value to store in ``field``.
            secret_id: Secret identifier, used in error messages only.

        Returns:
            The updated secret content, JSON-encoded; other fields are kept.

        Raises:
            RuntimeError: If ``content`` is not valid JSON.
            TypeError: If ``content`` is valid JSON but not a JSON object.

        """
        data = {} if content is None else VaultBase._load_json_object(content, secret_id)
        data[field] = value
        return json.dumps(data)

    @staticmethod
    def _load_json_object(content: str, secret_id: str) -> dict[str, object]:
        """Parse secret content that must be a JSON object.

        Raises:
            RuntimeError: If ``content`` is not valid JSON.
            TypeError: If ``content`` is valid JSON but not a JSON object.

        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            msg = f"Secret {secret_id!r} content is not valid JSON"
            raise RuntimeError(msg) from e
        if not isinstance(data, dict):
            msg = f"Secret {secret_id!r} content must be a JSON object"
            raise TypeError(msg)
        return cast("dict[str, object]", data)
