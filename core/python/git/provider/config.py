"""Configuration structures for git providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from credentials import add_credentials

# Pydantic needs this at runtime to build ProvidersConfig's schema, even
# though it is only used in a type annotation below.
from storage.config import StorageSectionConfig  # noqa: TC001

if TYPE_CHECKING:
    from credentials.base import CredentialsBase

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

    msg = f"Could not find {DEFAULT_PROVIDERS_CONFIG_RELATIVE_PATH} or {INSTALLED_PROVIDERS_CONFIG_GLOB}"
    raise FileNotFoundError(msg)


DEFAULT_PROVIDERS_CONFIG_PATH = _resolve_default_providers_config_path()

# Credentials of the "storage" provider are Nexus ones: it is the default
# backend of that provider and the only one needing explicit credentials
# (Azure/S3/OCI rely on their SDK default credential chain).
_STORAGE_PROVIDER_BACKEND = "nexus"


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    model_config = ConfigDict(extra="forbid")

    kwargs: dict[str, Any] = Field(default_factory=dict)
    auth_type: Literal["basic", "ssh"] = "basic"
    branches: list[str]


class ProvidersConfig(BaseModel):
    """Configuration for all providers and storage backends."""

    model_config = ConfigDict(extra="forbid")

    provider: dict[str, ProviderConfig]
    storage: StorageSectionConfig

    def get_credentials(self, provider_name: str) -> CredentialsBase | None:
        """Return environment-backed credentials for a provider.

        Args:
            provider_name: Name of the provider to resolve credentials for.
                ``"storage"`` resolves to Nexus credentials (see
                :data:`_STORAGE_PROVIDER_BACKEND`).

        Returns:
            The resolved credentials, or ``None`` if ``provider_name`` is not configured.

        """
        if provider_name == "storage":
            return add_credentials(_STORAGE_PROVIDER_BACKEND)

        provider_config = self.provider.get(provider_name)
        if provider_config is None:
            return None

        return add_credentials(provider_name, auth_type=provider_config.auth_type)

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
