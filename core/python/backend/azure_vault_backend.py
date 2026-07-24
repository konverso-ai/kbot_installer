"""Azure Key Vault authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from azure.keyvault.secrets import SecretClient

from utils.Logger import logger

if TYPE_CHECKING:
    from credentials.azure_credentials import AzureCredentials

log = logger.get_package_logger("backend")


class AzureVaultBackend:
    """Backend for Azure Key Vault secrets."""

    _client: SecretClient

    def __init__(self, credentials: AzureCredentials, vault_name: str) -> None:
        """Build the Azure Key Vault client from the given credentials.

        Args:
            credentials: Azure connection config used to resolve the
                authentication credential. Authentication itself is resolved
                by Azure's own default credential chain.
            vault_name: Name of the Azure Key Vault to connect to.

        """
        self.__credentials = credentials
        vault_uri = f"https://{vault_name}.vault.azure.net"
        self.__client = SecretClient(
            vault_url=vault_uri,
            credential=self.__credentials.get_credential(),
        )

    def get_client(self) -> SecretClient:
        """Return the Azure Key Vault client."""
        return self.__client
