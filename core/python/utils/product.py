"""Pydantic models for product definitions."""

# Pydantic model fields are validated at runtime; pylint infers FieldInfo on access.
# pylint: disable=no-member

from pathlib import Path
from typing import Annotated, Any, Literal

import json

import tomlkit
import xmltodict
from writer.factory import add_writer
from pydantic import (
    AliasChoices,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
    field_validator,
)
from utils.version import Version


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

    name: LocMapper | None = None
    description: LocMapper | None = None


class Build(BaseModel):
    """Build model."""

    timestamp: str = ""
    branch: str = ""
    commit: str = ""


class Parent(BaseModel):
    """Parent product reference."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(
        validation_alias=AliasChoices("@name", "name"),
        serialization_alias="@name",
    )


class Category(BaseModel):
    """Product category."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(
        validation_alias=AliasChoices("@name", "name"),
        serialization_alias="@name",
    )


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

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    name: str = Field(
        validation_alias=AliasChoices("@name", "name"),
        serialization_alias="@name",
    )
    version: Version = Field(
        default_factory=Version.empty,
        validation_alias=AliasChoices("@version", "version"),
        serialization_alias="@version",
    )
    doc: str | None = Field(
        default=None,
        validation_alias=AliasChoices("@doc", "doc"),
        serialization_alias="@doc",
    )
    build: Build | None = Field(
        default=None,
        validation_alias=AliasChoices("build", "@build"),
        serialization_alias="@build",
    )
    date: str = Field(
        default="",
        validation_alias=AliasChoices("@date", "date"),
        serialization_alias="@date",
    )
    type: str = Field(
        default="solution",
        validation_alias=AliasChoices("@type", "type"),
        serialization_alias="@type",
    )
    parents: Parents | None = None
    categories: Categories | None = None
    license: str | None = None
    display: LocDisplayMapper | None = None

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: Any) -> Version:
        return Version.parse(value)

    @field_validator("build", mode="before")
    @classmethod
    def _validate_build(cls, value: Any) -> Any:
        if isinstance(value, str):
            return Build(timestamp=value, branch="", commit="").model_dump()
        return value

    @field_validator("parents", mode="before")
    @classmethod
    def _validate_parents(cls, value: Any) -> Any:
        if isinstance(value, list):
            return {"parent": [{"@name": name} for name in value]}
        return value

    @field_validator("categories", mode="before")
    @classmethod
    def _validate_categories(cls, value: Any) -> Any:
        if isinstance(value, list):
            return {"category": [{"@name": name} for name in value]}
        return value

    @field_serializer("version")
    def _serialize_version(self, version: Version) -> str:
        return version.to_json_str()

    @property
    def parent_names(self) -> list[str]:
        """Return parent product names as a flat list."""
        if self.parents and self.parents.parent:
            return [parent.name for parent in self.parents.parent]
        return []

    @property
    def category_names(self) -> list[str]:
        """Return category names as a flat list."""
        if self.categories and self.categories.category:
            return [category.name for category in self.categories.category]
        return []

    @property
    def docs_list(self) -> list[str]:
        """Return documentation references parsed from the doc attribute."""
        if not self.doc:
            return []
        return [item.strip() for item in self.doc.split(",") if item.strip()]

    @property
    def build_timestamp(self) -> str | None:
        """Return the build timestamp when available."""
        if self.build and self.build.timestamp:
            return self.build.timestamp
        return None

    @classmethod
    def from_xml(cls, xml_content: str) -> "Product":
        """Create Product from XML content.

        Args:
            xml_content: XML string describing a product.

        Returns:
            Validated Product instance.

        Raises:
            ValueError: If XML is invalid or missing required fields.
        """
        try:
            parsed = xmltodict.parse(xml_content)
        except Exception as exc:
            msg = f"Invalid XML content: {exc}"
            raise ValueError(msg) from exc
        if "product" not in parsed:
            msg = "Root element must be 'product'"
            raise ValueError(msg)
        try:
            return cls.model_validate(parsed["product"])
        except ValidationError as exc:
            if any(
                error["loc"] in (("name",), ("@name",)) for error in exc.errors()
            ):
                msg = "Product name is required"
                raise ValueError(msg) from exc
            raise

    @classmethod
    def from_xml_file(cls, xml_path: str | Path) -> "Product":
        """Create Product from an XML file.

        Args:
            xml_path: Path to the XML file.

        Returns:
            Validated Product instance.

        Raises:
            FileNotFoundError: If the XML file does not exist.
            ValueError: If XML is invalid or missing required fields.
        """
        path = Path(xml_path)
        if not path.exists():
            msg = f"XML file not found: {path.name}"
            raise FileNotFoundError(msg)
        return cls.from_xml(path.read_text(encoding="utf-8"))

    @classmethod
    def from_json(cls, json_content: str | dict[str, Any]) -> "Product":
        """Create Product from JSON content.

        Args:
            json_content: JSON string or already-parsed dictionary.

        Returns:
            Validated Product instance.

        Raises:
            ValueError: If JSON is invalid or missing required fields.
        """
        try:
            data = (
                json.loads(json_content)
                if isinstance(json_content, str)
                else json_content
            )
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON content: {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "name" not in data:
            msg = "Product name is required"
            raise ValueError(msg)
        return cls.model_validate(data)

    @classmethod
    def from_json_file(cls, json_path: str | Path) -> "Product":
        """Create Product from a JSON file.

        Args:
            json_path: Path to the JSON file.

        Returns:
            Validated Product instance.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
            ValueError: If JSON is invalid or missing required fields.
        """
        path = Path(json_path)
        if not path.exists():
            msg = f"JSON file not found: {path.name}"
            raise FileNotFoundError(msg)
        return cls.from_json(path.read_text(encoding="utf-8"))

    @classmethod
    def merge(cls, xml_product: "Product", json_product: "Product") -> "Product":
        """Merge XML and JSON products, with JSON taking precedence.

        Args:
            xml_product: Product parsed from XML.
            json_product: Product parsed from JSON.

        Returns:
            Merged Product instance.

        Raises:
            ValueError: If product names do not match.
        """
        if xml_product.name != json_product.name:
            msg = (
                f"Product names don't match: {xml_product.name} != {json_product.name}"
            )
            raise ValueError(msg)

        build = json_product.build or xml_product.build
        return cls(
            name=xml_product.name,
            version=json_product.version or xml_product.version,
            doc=json_product.doc or xml_product.doc,
            build=build,
            date=json_product.date or xml_product.date,
            type=json_product.type or xml_product.type,
            parents=json_product.parents or xml_product.parents,
            categories=json_product.categories or xml_product.categories,
            license=json_product.license or xml_product.license,
            display=json_product.display or xml_product.display,
        )

    def to_xml(self) -> str:
        """Convert Product to XML string.

        Returns:
            XML representation of the product.
        """
        product: dict[str, Any] = {
            "@name": self.name,
            "@version": self.version.to_str(),
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
        data: dict[str, Any] = {
            "name": self.name,
            "version": self.version.to_json_str(),
            "date": self.date,
            "type": self.type,
            "parents": self.parent_names,
            "categories": self.category_names,
        }
        if self.build is not None:
            data["build"] = self.build.model_dump()
        if self.license is not None:
            data["license"] = self.license
        if self.display is not None:
            data["display"] = self.display.model_dump(exclude_none=True)
        if self.doc is not None:
            data["doc"] = self.doc
        return data

    def to_toml(self) -> str:
        """Convert Product to a TOML string."""
        return tomlkit.dumps(self.model_dump(mode="python", exclude_none=True))

    def export(self, mode: Literal["xml", "toml"], path: str | Path) -> None:
        """Export the product to a file in the given format.

        Args:
            mode: Serialization format (``xml`` or ``toml``).
            path: Destination file path.

        Raises:
            AttributeError: If no ``to_{mode}`` method exists on the product.
        """
        content = getattr(self, f"to_{mode}")()
        add_writer("text").write(content, path)
