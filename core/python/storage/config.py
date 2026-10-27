"""Configuration schemas for storage backends."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class NexusStorageSettings(BaseModel):
    """Nexus-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    repository: str


class S3StorageSettings(BaseModel):
    """S3-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    bucket_name: str
    cluster_name: str = ""
    region_name: str = "eu-west-1"


class AzureStorageSettings(BaseModel):
    """Azure-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    account_url: str
    container_name: str
    credential_type: Literal["default_azure", "client_secret"] = "default_azure"


class OciStorageSettings(BaseModel):
    """OCI Object Storage-specific storage backend settings."""

    model_config = ConfigDict(extra="forbid")

    bucket_name: str
    namespace_name: str
    region: str = "eu-frankfurt-1"


class StorageSectionConfig(BaseModel):
    """Settings for every storage backend, keyed by backend name."""

    model_config = ConfigDict(extra="forbid")

    nexus: NexusStorageSettings
    s3: S3StorageSettings
    azure: AzureStorageSettings
    oci: OciStorageSettings
