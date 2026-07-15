"""Configuration structures for providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from credentials import add_credentials

if TYPE_CHECKING:
    from auth.base import HttpAuthBase
    from credentials.base import (
        ClientSecretCredentialsBase,
        CredentialsBase,
        StorageCredentialsBase,
    )

DEFAULT_PROVIDERS_CONFIG_RELATIVE_PATH = Path("conf") / "default_providers_config.json"
INSTALLED_PROVIDERS_CONFIG_GLOB = "installer/*/conf/default_providers_config.json"


def _resolve_default_providers_config_path() -> Path:
    """Locate the default providers config file in dev or installed layouts."""
    for parent in Path(__file__).resolve().parents:
        dev_candidate = parent / DEFAULT_PROVIDERS_CONFIG_RELATIVE_PATH
        if dev_candidate.is_file():
            return dev_candidate

        for installed_candidate in sorted(parent.glob(INSTALLED_PROVIDERS_CONFIG_GLOB)):
            if installed_candidate.is_file():
                return installed_candidate

    msg = (
        f"Could not find {DEFAULT_PROVIDERS_CONFIG_RELATIVE_PATH} "
        f"or {INSTALLED_PROVIDERS_CONFIG_GLOB}"
    )
    raise FileNotFoundError(msg)


DEFAULT_PROVIDERS_CONFIG_PATH = _resolve_default_providers_config_path()


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    model_config = ConfigDict(extra="forbid")

    kwargs: dict[str, Any] = Field(default_factory=dict)
    env_vars: list[str]
    auth_type: Literal["basic", "ssh"] = "basic"
    branches: list[str]


class NexusStorageSettings(BaseModel):
    """Nexus-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    repository: str

    def storage_kwargs(self, auth: HttpAuthBase | None = None) -> dict[str, Any]:
        """Return kwargs for ``add_storage("nexus", ...)``."""
        return {
            "domain": self.domain,
            "repository": self.repository,
            "auth": auth,
        }


class S3StorageSettings(BaseModel):
    """S3-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    bucket_name: str
    cluster_name: str = ""
    region_name: str = "eu-west-1"
    env_vars: list[str] = Field(
        default_factory=lambda: ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    )

    def storage_kwargs(self, _auth: HttpAuthBase | None = None) -> dict[str, Any]:
        """Return kwargs for ``add_storage("s3", ...)``."""
        credentials = cast("StorageCredentialsBase", add_credentials("s3"))
        return {
            "bucket_name": self.bucket_name,
            "cluster_name": self.cluster_name or None,
            "region_name": self.region_name,
            **credentials.storage_kwargs(),
        }


class AzureStorageSettings(BaseModel):
    """Azure-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    account_url: str
    container_name: str
    credential_type: Literal["default_azure", "client_secret"] = "default_azure"
    env_vars: list[str] = Field(
        default_factory=lambda: [
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_CLIENT_SECRET",
        ]
    )

    def storage_kwargs(self, _auth: HttpAuthBase | None = None) -> dict[str, Any]:
        """Return kwargs for ``add_storage("azure", ...)``."""
        kwargs: dict[str, Any] = {
            "account_url": self.account_url,
            "container_name": self.container_name,
            "credential_type": self.credential_type,
        }
        if self.credential_type == "client_secret":
            kwargs.update(
                cast(
                    "ClientSecretCredentialsBase",
                    add_credentials("azure_storage", credential_type="client_secret"),
                ).client_secret_kwargs()
            )
        return kwargs


class OciStorageSettings(BaseModel):
    """OCI Object Storage-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    bucket_name: str
    namespace_name: str
    region: str = "eu-frankfurt-1"
    env_vars: list[str] = Field(
        default_factory=lambda: [
            "OCI_USER_OCID",
            "OCI_TENANCY_OCID",
            "OCI_FINGERPRINT",
            "OCI_PRIVATE_KEY_PATH",
        ]
    )

    def storage_kwargs(self, _auth: HttpAuthBase | None = None) -> dict[str, Any]:
        """Return kwargs for ``add_storage("oci", ...)``."""
        credentials = cast("StorageCredentialsBase", add_credentials("oci"))
        return {
            "bucket_name": self.bucket_name,
            "namespace_name": self.namespace_name,
            "region": self.region,
            **credentials.storage_kwargs(),
        }


class StorageSectionConfig(BaseModel):
    """Storage backend selection and per-backend settings."""

    model_config = ConfigDict(extra="forbid")

    backend: Literal["nexus", "s3", "azure", "oci"]
    nexus: NexusStorageSettings
    s3: S3StorageSettings
    azure: AzureStorageSettings
    oci: OciStorageSettings

    def get_backend_kwargs(self, auth: HttpAuthBase | None = None) -> dict[str, Any]:
        """Return kwargs for ``add_storage`` for the active backend."""
        settings = getattr(self, self.backend)
        return settings.storage_kwargs(auth)


class ProvidersConfig(BaseModel):
    """Configuration for all providers and storage backends."""

    model_config = ConfigDict(extra="forbid")

    provider: dict[str, ProviderConfig]
    storage: StorageSectionConfig

    def get_credentials(self, provider_name: str) -> CredentialsBase | None:
        """Return environment-backed credentials for a provider."""
        if provider_name == "storage":
            backend = self.storage.backend
            if backend == "azure":
                return add_credentials(
                    "azure_storage",
                    credential_type=self.storage.azure.credential_type,
                )
            return add_credentials(backend)

        if provider_name not in self.provider:
            return None

        provider_config = self.provider[provider_name]
        if provider_config.auth_type == "ssh":
            return add_credentials("ssh")

        return add_credentials(provider_name)

    def get_provider_config(self, provider_name: str) -> ProviderConfig | None:
        """Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider to get configuration for.

        Returns:
            ProviderConfig if found, None otherwise.

        """
        return self.provider.get(provider_name)

    def get_available_providers(self) -> list[str]:
        """Get list of configured provider names.

        Returns:
            List of provider names.

        """
        return list(self.provider.keys())


def load_default_providers_config(
    path: Path | None = None,
) -> ProvidersConfig:
    """Load provider configuration from a JSON file.

    Args:
        path: Path to the JSON configuration file.
            Defaults to ``conf/default_providers_config.json``.

    Returns:
        Parsed provider configuration.

    """
    config_path = path or DEFAULT_PROVIDERS_CONFIG_PATH
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return ProvidersConfig.model_validate(data)


DEFAULT_PROVIDERS_CONFIG = load_default_providers_config()
