"""Azure storage credential requirements."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias, cast

from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import override

from credentials.base import ClientSecretCredentialsBase
from credentials.factory import create_credentials

AzureCredentialType: TypeAlias = Annotated[
    Literal["default_azure", "client_secret"],
    Field(default="default_azure"),
]


class AzureStorageCredentials(BaseSettings):
    """Azure storage credentials, with optional client-secret env requirements."""

    model_config = SettingsConfigDict(extra="ignore")

    credential_type: AzureCredentialType
    _client_secret: ClientSecretCredentialsBase = PrivateAttr()

    @override
    def model_post_init(self, __context: Any, __config: Any) -> None:
        """Initialize nested client-secret credentials."""
        self._client_secret = cast(
            ClientSecretCredentialsBase,
            create_credentials("azure_client_secret"),
        )

    def missing_env_vars(self) -> list[str]:
        if self.credential_type == "default_azure":
            return []
        return self._client_secret.missing_env_vars()

    def auth_kwargs(self) -> dict[str, str] | None:
        return None

    def client_secret_kwargs(self) -> dict[str, str | None]:
        """Return Azure client-secret fields for storage backend construction."""
        return self._client_secret.client_secret_kwargs()
