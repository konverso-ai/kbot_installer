"""Secret vault abstractions."""

from abc import ABC, abstractmethod


class VaultBase(ABC):
    """Abstract base class for secret vault operations."""

    @abstractmethod
    def get(self, key: str) -> str:
        """Retrieve a secret value from the vault.

        Args:
            key: Secret key in the ``<vault-name>::<key-in-vault>`` form.

        Returns:
            The secret value.

        Raises:
            ValueError: If ``key`` is not in the ``<vault-name>::<key-in-vault>`` form.

        """

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
