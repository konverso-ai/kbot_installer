"""Pydantic models describing git repositories managed by the installer."""

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel

from utils.product import Product
from utils.settings import Settings


class GitProtocol(Enum):
    """Git protocol."""

    HTTPS = "https"
    SSH = "ssh"


class GitProvider(Enum):
    """Git provider."""

    GITHUB = "github"
    BITBUCKET = "bitbucket"
    STORAGE = "storage"


class RepoType(Enum):
    """Repository type."""

    SITE = "site"
    CURTOMER = "customer"


class GitRepo(BaseModel):
    """Git repository model."""

    name: str
    protocol: GitProtocol
    provider: GitProvider
    type: RepoType
    product: Product
    settings: Any

    def export(self) -> dict[str, str]:
        """Export repository files as relative paths mapped to file contents."""
        return {
            "pyproject.toml": self.product.to_toml(),
            "description.xml": self.product.to_xml(),
            "conf/kbot.conf": self.settings.to_conf(),
            "conf/kbot.json": _settings_json(self.settings),
        }


def _settings_json(settings: Settings | Any) -> str:
    """Serialize settings to a JSON string for file export."""
    content = settings.to_json()
    if isinstance(content, str):
        return content
    return json.dumps(content)
