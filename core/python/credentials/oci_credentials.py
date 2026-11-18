"""Oracle Cloud Infrastructure (OCI) default credentials, config only."""

from typing import Annotated, Literal, TypeAlias, cast

import oci
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

OciAuthMethod: TypeAlias = Literal["config_file", "instance_principal", "resource_principal"]
OciRegion: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="OCI_REGION"),
]
OciConfigProfile: TypeAlias = Annotated[
    str,
    Field(default="DEFAULT", validation_alias="OCI_CONFIG_PROFILE"),
]
OciAuth: TypeAlias = Annotated[
    OciAuthMethod,
    Field(default="config_file", validation_alias="OCI_AUTH_METHOD"),
]


class OciCredentials(BaseSettings):
    """OCI connection config for the default OCI credentials.

    This credential type requires nothing beyond connection config: actual
    authentication is resolved either by the OCI SDK's own default config file
    (``~/.oci/config``, or ``OCI_CONFIG_FILE``/``OCI_CONFIG_PROFILE`` when set),
    or by the instance/resource principal selected via ``OCI_AUTH_METHOD``.
    """

    model_config = SettingsConfigDict(extra="ignore")

    region: OciRegion
    config_profile: OciConfigProfile
    auth_method: OciAuth

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            An empty list: this credential type relies on the OCI SDK's own
            default authentication and requires nothing from the environment.

        """
        return []

    def storage_kwargs(self) -> dict[str, str | None]:
        """Return credential fields for storage backend construction.

        Returns:
            An empty dict: authentication is resolved entirely by the OCI
            SDK, so no extra fields need to be merged in.

        """
        return {}

    def to_client_config(self) -> dict[str, str | None]:
        """Build the OCI client config dict used to construct SDK clients.

        Returns:
            With ``config_file`` authentication, the config dict loaded from the
            OCI SDK's default config file (``~/.oci/config`` unless overridden via
            ``OCI_CONFIG_FILE``); with principal authentication, an empty dict.
            ``region`` is overridden when explicitly configured.

        """
        if self.auth_method == "config_file":
            config = cast(
                "dict[str, str | None]",
                oci.config.from_file(profile_name=self.config_profile),
            )
        else:
            config = {}
        if self.region:
            config["region"] = self.region
        return config

    def to_signer(self) -> oci.signer.AbstractBaseSigner | None:
        """Build the request signer for principal authentication.

        Returns:
            The instance or resource principal signer, or None with
            ``config_file`` authentication (the SDK then signs from the config).

        """
        if self.auth_method == "instance_principal":
            return oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        if self.auth_method == "resource_principal":
            return cast(
                "oci.signer.AbstractBaseSigner",
                oci.auth.signers.get_resource_principals_signer(),
            )
        return None
