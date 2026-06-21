"""Bundle model for grouping product versions."""

import json
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator,
)

from utils.version import Version
from utils.product import Product


def _parse_version(value: Any) -> Version:
    if isinstance(value, Version):
        return value
    if isinstance(value, str):
        return Version(value)
    raise TypeError(f"Expected version string or Version, got {type(value).__name__}")


class Bundle(BaseModel):
    """Bundle model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    version: Version
    created_by: str
    created_on: str
    created_from: str
    timestamp: str
    versions: list[Product]

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: Any) -> Version:
        return _parse_version(value)

    @field_serializer("version")
    def _serialize_version(self, version: Version) -> str:
        return version.to_str()

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
