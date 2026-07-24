"""Bundle model for grouping product versions."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator, computed_field,
)

from utils.product import Product
from utils.version import Version
from writer.factory import add_writer


class Bundle(BaseModel):
    """Bundle model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    version: Version
    created_by: str = ""
    created_on: str = ""
    created_from: str = ""
    timestamp: str = ""
    versions: list[Product]

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: Any) -> Version:
        version = Version.parse(value)
        if not version:
            msg = "Bundle version is required"
            raise ValueError(msg)
        return version

    @field_serializer("version")
    def _serialize_version(self, version: Version) -> str:
        return version.to_str()

    @classmethod
    def file_name(cls, name: str, version: Version | None = None) -> Path:
        """Return the file name for this bundle."""
        if version is None:
            return Path(f"{name}.json")
        return Path(f"{name}-{version}.json")

    @classmethod
    def from_name(cls, name: str) -> "Bundle":
        name, version = name.rsplit("-", 1)
        return cls(name=name, version=Version.parse(version))

    @classmethod
    def from_json(cls, json_content: str | dict[str, Any]) -> "Bundle":
        """Create Bundle from JSON content.

        Args:
            json_content: JSON string or already-parsed dictionary.

        Returns:
            Validated Bundle instance.

        """
        data = (
            json.loads(json_content)
            if isinstance(json_content, str)
            else json_content
        )
        return cls.model_validate(data)

    def to_json(self) -> dict[str, Any]:
        """Convert Bundle to a JSON-serializable dictionary.

        Returns:
            Dictionary representation suitable for :meth:`from_json` round-trip.

        """
        return {
            "name": self.name,
            "version": self.version.to_json_str(),
            "created_by": self.created_by,
            "created_on": self.created_on,
            "created_from": self.created_from,
            "timestamp": self.timestamp,
            "versions": [product.to_json() for product in self.versions],
        }

    def export(self, mode: Literal["json"], path: str | Path | None = None) -> None:
        """Export the bundle to a file in the given format.

        Args:
            mode: Serialization format (``json``).
            path: Destination file path. If ``None``, uses the default file name.

        Raises:
            AttributeError: If no ``to_{mode}`` method exists on the bundle.

        """
        content = getattr(self, f"to_{mode}")()
        if not isinstance(content, str):
            content = json.dumps(content, indent=4)
        if path is None:
            path = self.file_name(self.name, self.version)
        add_writer("text").write(content, path)
