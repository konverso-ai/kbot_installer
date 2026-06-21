from enum import Enum
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from utils.path_utils import ensure_file_path
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

    def export(self) -> dict[Path, str]:
        """Export the repository to a file."""
        return {
            ensure_file_path("pyproject.toml"): self.product.to_toml(),
            ensure_file_path("description.xml"): self.product.to_xml(),
            ensure_file_path(Path("conf") / "kbot.conf"): self.settings.to_conf(),
            ensure_file_path(Path("conf") / "kbot.json"): _settings_json(
                self.settings
            ),
        }


def _settings_json(settings: Settings | Any) -> str:
    """Serialize settings to a JSON string for file export."""
    content = settings.to_json()
    if isinstance(content, str):
        return content
    return json.dumps(content)
