"""HashiCorp Vault credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

VaultAddr: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="VAULT_ADDR"),
]
VaultToken: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="VAULT_TOKEN"),
]


class HashicorpCredentials(BaseSettings):
    """HashiCorp Vault server address and token loaded from the environment.

    TLS settings (``VAULT_CACERT``, ``VAULT_CLIENT_CERT``, ...) are read by the
    ``hvac`` client itself.
    """

    model_config = SettingsConfigDict(extra="ignore")

    url: VaultAddr
    token: VaultToken

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            Names of the HashiCorp Vault environment variables that are not set.

        """
        missing: list[str] = []
        if not self.url:
            missing.append("VAULT_ADDR")
        if not self.token:
            missing.append("VAULT_TOKEN")
        return missing
