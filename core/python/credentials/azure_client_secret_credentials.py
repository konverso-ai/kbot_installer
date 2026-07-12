"""Azure client-secret credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AzureTenantId: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="AZURE_TENANT_ID"),
]
AzureClientId: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="AZURE_CLIENT_ID"),
]
AzureClientSecret: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="AZURE_CLIENT_SECRET"),
]


class AzureClientSecretCredentials(BaseSettings):
    """Azure service-principal credentials loaded from the environment."""

    model_config = SettingsConfigDict(extra="ignore")

    tenant_id: AzureTenantId
    client_id: AzureClientId
    client_secret: AzureClientSecret

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            Names of the Azure service-principal environment variables that
            are not set.

        """
        missing: list[str] = []
        if not self.tenant_id:
            missing.append("AZURE_TENANT_ID")
        if not self.client_id:
            missing.append("AZURE_CLIENT_ID")
        if not self.client_secret:
            missing.append("AZURE_CLIENT_SECRET")
        return missing

    def auth_kwargs(self) -> dict[str, str] | None:
        """Return HTTP auth constructor kwargs.

        Returns:
            None, as service-principal credentials are not used for HTTP auth.

        """
        return None

    def client_secret_kwargs(self) -> dict[str, str | None]:
        """Return Azure client-secret fields for storage backend construction."""
        return self.model_dump()
