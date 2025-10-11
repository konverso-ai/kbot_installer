"""Azure vault implementation for Azure Key Vault integration."""

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from kbot_installer.core.vault.vault_base import VaultBase, VaultError


class AzureVault(VaultBase):
    """Azure vault implementation.

    This vault implementation provides integration with Azure Key Vault
    for secure key-value storage operations.
    """

    _name: str = "AZUREKEYVAULT"

    def __init__(self) -> None:
        """Initialize the Azure vault."""
        self._credential = DefaultAzureCredential()

    @property
    def vault_url(self) -> str:
        """Get the vault URL for the Azure vault.

        Returns:
            str: The vault URL for the Azure vault.

        """
        return f"https://{self._name}.vault.azure.net"

    def _get_secret_client(self) -> SecretClient:
        """Get the secret client for the Azure vault.

        Returns:
            SecretClient: The secret client for the Azure vault.

        """
        try:
            client = SecretClient(vault_url=self.vault_url, credential=self._credential)
        except Exception as e:
            msg = f"Failed to get secret client for Azure vault: {e}"
            raise VaultError(msg) from e
        return client

    @classmethod
    def get_name(cls) -> str:
        """Get the name of the vault.

        Returns:
            str: The name identifier for this vault class.

        """
        return cls._name

    def get_value(self, key: str) -> str | None:
        """Get the value for a given key from the Azure vault.

        Args:
            key (str): The key to retrieve the value for.

        Returns:
            str | None: The value associated with the key, or None if not found.

        """
        if not key:
            return None

        if "::" not in key:
            return None

        _, secret_name = key.split("::")

        if not secret_name:
            return None

        return self._get_secret_client().get_secret(secret_name).value

    def set_value(self, key: str, value: str) -> bool:
        """Add a key-value pair to the Azure vault.

        Args:
            key (str): The key to store.
            value (str): The value to associate with the key.

        Returns:
            bool: True on success, False on failure.

        """
        if not key or value is None:
            return False

        try:
            client = self._get_secret_client()
            client.set_secret(key, value)

        except Exception:
            return False

        return True

    def delete_value(self, key: str) -> bool:
        """Delete a given key from the Azure vault.

        Args:
            key (str): The key to delete.

        Returns:
            bool: True on success, False on failure.

        """
        if not key:
            return False

        try:
            client = self._get_secret_client()
            client.begin_delete_secret(key)

        except Exception:
            return False

        return True
