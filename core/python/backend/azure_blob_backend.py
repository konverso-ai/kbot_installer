"""Azure Blob Storage authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from azure.storage.blob import BlobServiceClient

from utils.Logger import logger

if TYPE_CHECKING:
    from credentials.azure_credentials import AzureCredentials

log = logger.get_package_logger("backend")


class AzureBlobBackend:
    """Backend for Azure Blob Storage."""

    _client: BlobServiceClient

    def __init__(self, account_url: str, credentials: AzureCredentials) -> None:
        """Build the Azure Blob Storage client from the given account URL and credentials.

        Args:
            account_url: URL of the Azure Storage account to connect to
                (e.g. ``https://{account}.blob.core.windows.net``). This is
                connection configuration, not a credential.
            credentials: Azure credentials used to authenticate. Authentication
                itself is resolved by Azure's own default credential chain.

        """
        self.__credentials = credentials
        self.__client = BlobServiceClient(
            account_url=account_url,
            credential=self.__credentials.get_credential(),
        )

    def get_client(self) -> BlobServiceClient:
        """Return the Azure Blob Storage client."""
        return self.__client
