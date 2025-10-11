"""Environment vault implementation for environment variable storage."""

import os

from kbot_installer.core.vault.vault_base import VaultBase


class EnvironmentVault(VaultBase):
    """Environment vault implementation.

    This vault implementation provides access to environment variables
    for key-value storage operations.
    """

    _name: str = "VARIABLE"

    @classmethod
    def get_name(cls) -> str:
        """Get the name of the vault.

        Returns:
            str: The name identifier for this vault class.

        """
        return cls._name

    def get_value(self, key: str) -> str | None:
        """Get the value for a given key from environment variables.

        Args:
            key (str): The key to retrieve the value for.

        Returns:
            str | None: The value associated with the key, or None if not found.

        """
        if not key:
            return None

        try:
            return os.environ[key]
        except KeyError:
            return ""

    def set_value(self, key: str, value: str) -> bool:
        """Add a key-value pair to the environment variables.

        Args:
            key (str): The key to store.
            value (str): The value to associate with the key.

        Returns:
            bool: True on success, False on failure.

        """
        msg = "Setting values in environment variables is not supported"
        raise NotImplementedError(msg)

    def delete_value(self, key: str) -> bool:
        """Delete a given key from the environment variables.

        Args:
            key (str): The key to delete.

        Returns:
            bool: True on success, False on failure.

        """
        msg = "Deleting values from environment variables is not supported"
        raise NotImplementedError(msg)
