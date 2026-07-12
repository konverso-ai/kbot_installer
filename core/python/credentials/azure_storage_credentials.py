"""Azure storage credential requirements."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias, cast

from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import override

from credentials.base import ClientSecretCredentialsBase
from credentials.factory import add_credentials

AzureCredentialType: TypeAlias = Annotated[
    Literal["default_azure", "client_secret"],
    Field(default="default_azure"),
]


class AzureStorageCredentials(BaseSettings):
    """Azure storage credentials, with optional client-secret env requirements."""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="BUNDLE_")

    credential_type: AzureCredentialType

    azure_blob_url: str | None = Field(default=None)
    provider: str | None = Field(default=None)

    _client_secret: ClientSecretCredentialsBase = PrivateAttr()

    @override
    def model_post_init(self, __context: Any) -> None:
        """Initialize nested client-secret credentials."""
        self._client_secret = cast(
            "ClientSecretCredentialsBase",
            add_credentials("azure_client_secret"),
        )

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            An empty list when using default Azure credentials, otherwise the
            missing client-secret environment variable names.

        """
        if self.credential_type == "default_azure":
            return []
        return self._client_secret.missing_env_vars()

    def auth_kwargs(self) -> dict[str, str] | None:
        """Return HTTP auth constructor kwargs.

        Returns:
            None, as Azure storage credentials are not used for HTTP auth.

        """
        return None

    def client_secret_kwargs(self) -> dict[str, str | None]:
        """Return Azure client-secret fields for storage backend construction."""
        return self._client_secret.client_secret_kwargs()
