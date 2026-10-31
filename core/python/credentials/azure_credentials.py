"""Azure Blob Storage default credentials."""

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureCredentials(BaseSettings):
    """Azure default credential chain resolver.

    This credential type requires no configuration of its own: actual
    authentication is resolved by Azure's own default credential chain
    (environment variables, managed identity, or the Azure CLI, in order).
    Connection details such as ``account_url`` are not credentials and are
    not part of this class; they belong to the backend/storage that uses it.
    """

    model_config = SettingsConfigDict(extra="ignore")

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            An empty list: this credential type relies on Azure's default
            credential chain and requires nothing from the environment.

        """
        return []

    def get_credential(self) -> TokenCredential:
        """Build the Azure token credential used to construct SDK clients.

        Returns:
            A ``DefaultAzureCredential`` instance, resolving credentials from
            the environment, a managed identity, the Azure CLI, or other
            supported sources, in order.

        """
        return DefaultAzureCredential()
