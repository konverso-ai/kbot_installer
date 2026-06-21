"""Pydantic models for product definitions."""

from typing import Annotated, Any

import json

import tomlkit
import xmltodict
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)


def _as_list(value: Any) -> list[Any]:
    if not value:
        return []
    return value if isinstance(value, list) else [value]


class LocMapper(BaseModel):
    """Localization mapper model."""

    en: str
    fr: str | None = None
    de: str | None = None
    it: str | None = None
    es: str | None = None
    pt: str | None = None


class LocDisplayMapper(BaseModel):
    """Localization display mapper model."""

    name: LocMapper
    description: LocMapper


class Build(BaseModel):
    """Build model."""

    timestamp: str = ""
    branch: str = ""
    commit: str = ""


class Parent(BaseModel):
    """Parent product reference."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="@name")


class Category(BaseModel):
    """Product category."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="@name")


class Parents(BaseModel):
    """Product parents container."""

    parent: Annotated[list[Parent], BeforeValidator(_as_list)] = Field(
        default_factory=list
    )


class Categories(BaseModel):
    """Product categories container."""

    category: Annotated[list[Category], BeforeValidator(_as_list)] = Field(
        default_factory=list
    )


class Product(BaseModel):
    """Product model."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = Field(alias="@name")
    version: str = Field(alias="@version", default="")
    doc: str | None = Field(alias="@doc", default=None)
    build: Build | None = None
    date: str = Field(alias="@date", default="")
    type: str = Field(alias="@type", default="solution")
    parents: Parents | None = None
    categories: Categories | None = None
    license: str | None = None
    display: LocDisplayMapper | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        for field, item in (("parents", "parent"), ("categories", "category")):
            if isinstance(values := normalized.get(field), list):
                normalized[field] = {item: [{"name": name} for name in values]}
        build_value = normalized.pop("@build", None)
        if build_value is None and isinstance(normalized.get("build"), str):
            build_value = normalized.pop("build")
        if isinstance(build_value, str):
            normalized["build"] = Build(
                timestamp=build_value, branch="", commit=""
            ).model_dump()
        return normalized

    @classmethod
    def from_xml(cls, xml_content: str) -> "Product":
        """Create Product from XML content.

        Args:
            xml_content: XML string describing a product.

        Returns:
            Validated Product instance.
        """
        return cls.model_validate(xmltodict.parse(xml_content)["product"])

    @classmethod
    def from_json(cls, json_content: str | dict[str, Any]) -> "Product":
        """Create Product from JSON content.

        Args:
            json_content: JSON string or already-parsed dictionary.

        Returns:
            Validated Product instance.
        """
        data = (
            json.loads(json_content)
            if isinstance(json_content, str)
            else json_content
        )
        return cls.model_validate(data)

    def to_xml(self) -> str:
        """Convert Product to XML string.

        Returns:
            XML representation of the product.
        """
        product: dict[str, Any] = {
            "@name": self.name,
            "@version": self.version,
            "@date": self.date,
            "@type": self.type,
        }
        if self.doc is not None:
            product["@doc"] = self.doc
        if self.build is not None:
            product["@build"] = self.build.timestamp
        if self.parents and self.parents.parent:
            product["parents"] = {
                "parent": [{"@name": parent.name} for parent in self.parents.parent]
            }
        if self.categories and self.categories.category:
            product["categories"] = {
                "category": [
                    {"@name": category.name} for category in self.categories.category
                ]
            }
        return xmltodict.unparse({"product": product}, pretty=True)

    def to_json(self) -> dict[str, Any]:
        """Convert Product to a JSON-serializable dictionary."""
        return self.model_dump(exclude_none=True) | {
            "parents": [p.name for p in self.parents.parent] if self.parents else [],
            "categories": (
                [c.name for c in self.categories.category] if self.categories else []
            ),
        }

    def to_toml(self) -> str:
        """Convert Product to a TOML string."""
        return tomlkit.dumps(self.model_dump(mode="python", exclude_none=True))