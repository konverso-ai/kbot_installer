"""Azure Blob Storage authentication and client management."""

import logging
from typing import Annotated, Any, Literal

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from backend.base import BackendBase
from pydantic import ConfigDict, Field, PrivateAttr
from typing_extensions import override

log = logging.getLogger(__name__)


class AzureBackend(BackendBase):
    """Backend for Azure Blob Storage."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    account_url: str
    credential_type: Annotated[Literal["default_azure", "client_secret"], Field(default="default_azure")]

    tenant_id: Annotated[str | None, Field(default=None)]
    client_id: Annotated[str | None, Field(default=None)]
    client_secret: Annotated[str | None, Field(default=None)]

    _client: BlobServiceClient | None = PrivateAttr(default=None)

    def _get_credential(self) -> Any:
        """Return the Azure credential."""
        if self.credential_type == "default_azure":
            return DefaultAzureCredential()
        if self.credential_type == "client_secret":
            if not self.tenant_id or not self.client_id or not self.client_secret:
                msg = "tenant_id, client_id, and client_secret are required for client_secret credential"
                raise ValueError(msg)
            return ClientSecretCredential(
                self.tenant_id,
                self.client_id,
                self.client_secret,
            )
        msg = f"Unsupported credential_type: {self.credential_type}"
        raise ValueError(msg)

    def model_post_init(self, __context: Any) -> None:
        """Initialize the Azure backend."""
        self._client = BlobServiceClient(
            account_url=self.account_url,
            credential=self._get_credential(),
        )

    @override
    def get_client(self) -> BlobServiceClient:
        """Return the Azure Blob Storage client."""
        if self._client is None:
            msg = "Azure Blob Storage client is not initialized"
            raise RuntimeError(msg)
        return self._client
