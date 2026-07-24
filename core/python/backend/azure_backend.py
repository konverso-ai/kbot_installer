"""Azure Blob Storage authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from azure.storage.blob import BlobServiceClient

from utils.Logger import logger

if TYPE_CHECKING:
    from credentials.azure_credentials import AzureCredentials

log = logger.get_package_logger("backend")


class AzureBackend:
    """Backend for Azure Blob Storage."""

    _client: BlobServiceClient

    def __init__(self, credentials: AzureCredentials) -> None:
        """Build the Azure Blob Storage client from the given credentials.

        Args:
            credentials: Azure connection config used to configure the
                underlying client. Authentication itself is resolved by
                Azure's own default credential chain.

        Raises:
            ValueError: If ``credentials.account_url`` is not set.

        """
        self.__credentials = credentials
        if self.__credentials.account_url is None:
            msg = "AzureCredentials.account_url must be set to build an AzureBackend"
            raise ValueError(msg)
        self.__client = BlobServiceClient(
            account_url=self.__credentials.account_url,
            credential=self.__credentials.get_credential(),
        )

    def get_client(self) -> BlobServiceClient:
        """Return the Azure Blob Storage client."""
        return self.__client
