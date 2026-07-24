"""Oracle Cloud Infrastructure (OCI) default credentials, config only."""

from typing import Annotated, TypeAlias

import oci
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

OciRegion: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="OCI_REGION"),
]
OciConfigProfile: TypeAlias = Annotated[
    str,
    Field(default="DEFAULT", validation_alias="OCI_CONFIG_PROFILE"),
]


class OciCredentials(BaseSettings):
    """OCI connection config for the default OCI config-file credentials.

    This credential type requires nothing beyond connection config: actual
    authentication is resolved by the OCI SDK's own default config file
    (``~/.oci/config``, or ``OCI_CONFIG_FILE``/``OCI_CONFIG_PROFILE`` when set).
    """

    model_config = SettingsConfigDict(extra="ignore")

    region: OciRegion
    config_profile: OciConfigProfile

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            An empty list: this credential type relies on the OCI SDK's own
            default config file and requires nothing from the environment.

        """
        return []

    def storage_kwargs(self) -> dict[str, str | None]:
        """Return credential fields for storage backend construction.

        Returns:
            An empty dict: authentication is resolved entirely by the OCI
            SDK's own default config file, so no extra fields need to be
            merged in.

        """
        return {}

    def to_client_config(self) -> dict[str, str | None]:
        """Build the OCI client config dict used to construct SDK clients.

        Returns:
            The config dict loaded from the OCI SDK's default config file
            (``~/.oci/config`` unless overridden via ``OCI_CONFIG_FILE``),
            with ``region`` overridden when explicitly configured.

        """
        config = oci.config.from_file(profile_name=self.config_profile)
        if self.region:
            config["region"] = self.region
        return config
