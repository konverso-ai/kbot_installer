"""Configuration structures for providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_PROVIDERS_CONFIG_RELATIVE_PATH = Path("conf") / "default_providers_config.json"


def _resolve_default_providers_config_path() -> Path:
    """Locate the default providers config file in dev or installed layouts."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / DEFAULT_PROVIDERS_CONFIG_RELATIVE_PATH
        if candidate.is_file():
            return candidate

    msg = f"Could not find {DEFAULT_PROVIDERS_CONFIG_RELATIVE_PATH}"
    raise FileNotFoundError(msg)


DEFAULT_PROVIDERS_CONFIG_PATH = _resolve_default_providers_config_path()


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    model_config = ConfigDict(extra="forbid")

    kwargs: dict[str, Any] = Field(default_factory=dict)
    env_vars: list[str]
    auth_type: str
    auth_params: dict[str, str]
    branches: list[str]


class ProvidersConfig(BaseModel):
    """Configuration for all providers."""

    model_config = ConfigDict(extra="forbid")

    providers: dict[str, ProviderConfig]

    def get_provider_config(self, provider_name: str) -> ProviderConfig | None:
        """Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider to get configuration for.

        Returns:
            ProviderConfig if found, None otherwise.

        """
        return self.providers.get(provider_name)

    def get_available_providers(self) -> list[str]:
        """Get list of configured provider names.

        Returns:
            List of provider names.

        """
        return list(self.providers.keys())


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
