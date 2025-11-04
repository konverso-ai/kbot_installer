"""Alias vault implementation for simple key-value storage."""

from kbot_installer.core.vault.vault_base import VaultBase


class AliasVault(VaultBase):
    """Alias vault implementation.

    This vault implementation provides a simple alias-based storage mechanism
    where keys are mapped to a predefined alias name.
    """

    _name: str = "ALIAS"

    @classmethod
    def get_name(cls) -> str:
        """Get the name of the vault.

        Returns:
            str: The alias name for this vault class.

        """
        return cls._name

    def get_value(self, key: str) -> str | None:
        """Get the value for a given key from the vault.

        For alias vault, this always returns the vault's name as the value.

        Args:
            key (str): The key to retrieve the value for.

        Returns:
            str | None: The vault's name, or None if key is invalid.

        """
        if not key:
            return None
        return self._name

    def set_value(self, key: str, value: str) -> bool:
        """Add a key-value pair to the vault.

        For alias vault, this operation is not supported as the value
        is always the vault's name.

        Args:
            key (str): The key to store.
            value (str): The value to associate with the key.

        Returns:
            bool: Always returns False as this operation is not supported.

        """
        msg = "Setting values in alias vault is not supported"
        raise NotImplementedError(msg)

    def delete_value(self, key: str) -> bool:
        """Delete a given key from the vault.

        For alias vault, this operation is not supported as keys
        are not actually stored.

        Args:
            key (str): The key to delete.

        Returns:
            bool: Always returns False as this operation is not supported.

        """
        msg = "Deleting values from alias vault is not supported"
        raise NotImplementedError(msg)
