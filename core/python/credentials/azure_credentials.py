"""Azure Blob Storage default credentials, config only."""

from typing import Annotated

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureCredentials(BaseSettings):
    """Azure Blob Storage connection config for the default credential chain.

    This credential type requires nothing beyond connection config: actual
    authentication is resolved by Azure's own default credential chain
    (environment variables, managed identity, or the Azure CLI, in order).
    """

    model_config = SettingsConfigDict(extra="ignore")

    account_url: Annotated[str | None, Field(default=None)]
    container_name: Annotated[str | None, Field(default=None)]

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
