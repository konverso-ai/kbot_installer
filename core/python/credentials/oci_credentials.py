"""Oracle Cloud Infrastructure (OCI) credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

OciUserOcid: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="OCI_USER_OCID"),
]
OciTenancyOcid: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="OCI_TENANCY_OCID"),
]
OciFingerprint: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="OCI_FINGERPRINT"),
]
OciPrivateKeyPath: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="OCI_PRIVATE_KEY_PATH"),
]
OciPassPhrase: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="OCI_PASS_PHRASE"),
]


class OciCredentials(BaseSettings):
    """OCI API-key credentials loaded from the environment."""

    model_config = SettingsConfigDict(extra="ignore")

    user_ocid: OciUserOcid
    tenancy_ocid: OciTenancyOcid
    fingerprint: OciFingerprint
    private_key_path: OciPrivateKeyPath
    pass_phrase: OciPassPhrase

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            Names of the OCI environment variables that are not set.

        """
        missing: list[str] = []
        if not self.user_ocid:
            missing.append("OCI_USER_OCID")
        if not self.tenancy_ocid:
            missing.append("OCI_TENANCY_OCID")
        if not self.fingerprint:
            missing.append("OCI_FINGERPRINT")
        if not self.private_key_path:
            missing.append("OCI_PRIVATE_KEY_PATH")
        return missing

    def auth_kwargs(self) -> dict[str, str] | None:
        """Return HTTP auth constructor kwargs.

        Returns:
            None, as OCI credentials are not used for HTTP auth.

        """
        return None

    def storage_kwargs(self) -> dict[str, str | None]:
        """Return OCI credential fields for storage backend construction."""
        return {
            "user_ocid": self.user_ocid,
            "tenancy_ocid": self.tenancy_ocid,
            "fingerprint": self.fingerprint,
            "private_key_path": self.private_key_path,
            "pass_phrase": self.pass_phrase,
        }
