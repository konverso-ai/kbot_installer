"""Product class for managing product definitions."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xml.dom.minidom import parse

from xml.etree import ElementTree as ET


from defusedxml import ElementTree as defused_ET


@dataclass
class Product:
    """Represents a product with its metadata and dependencies.

    Attributes:
        name: Product name.
        version: Product version.
        build: Build information.
        date: Build date.
        type: Product type (solution, framework, customer).
        parents: List of parent product names (dependencies).
        categories: List of product categories.
        license: License information.
        display: Multilingual display information.
        build_details: Detailed build information (timestamp, branch, commit).

    """

    name: str
    version: str
    build: str | None = None
    date: str | None = None
    type: str = "solution"
    parents: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    license: str | None = None
    display: dict[str, Any] | None = None
    build_details: dict[str, Any] | None = None

    @classmethod
    def from_xml(cls, xml_content: str) -> "Product":
        """Create Product from XML content.

        Args:
            xml_content: XML string content.

        Returns:
            Product instance.

        Raises:
            ValueError: If XML is invalid or missing required fields.

        """
        try:
            root = defused_ET.fromstring(xml_content)
        except defused_ET.ParseError as e:
            msg = f"Invalid XML content: {e}"
            raise ValueError(msg) from e

        if root.tag != "product":
            msg = "Root element must be 'product'"
            raise ValueError(msg)

        # Extract attributes
        name = root.get("name")
        if not name:
            msg = "Product name is required"
            raise ValueError(msg)

        version = root.get("version", "")
        build = root.get("build") or None
        date = root.get("date") or None
        product_type = root.get("type", "solution")

        # Extract parents
        parents = []
        parents_elem = root.find("parents")
        if parents_elem is not None:
            for parent_elem in parents_elem.findall("parent"):
                parent_name = parent_elem.get("name")
                if parent_name:
                    parents.append(parent_name)

        # Extract categories
        categories = []
        categories_elem = root.find("categories")
        if categories_elem is not None:
            for category_elem in categories_elem.findall("category"):
                category_name = category_elem.get("name")
                if category_name:
                    categories.append(category_name)

        return cls(
            name=name,
            version=version,
            build=build,
            date=date,
            type=product_type,
            parents=parents,
            categories=categories,
        )

    @classmethod
    def from_json(cls, json_content: str) -> "Product":
        """Create Product from JSON content.

        Args:
            json_content: JSON string content.

        Returns:
            Product instance.

        Raises:
            ValueError: If JSON is invalid or missing required fields.

        """
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON content: {e}"
            raise ValueError(msg) from e

        if "name" not in data:
            msg = "Product name is required"
            raise ValueError(msg)

        # Extract build details if present
        build_details = data.get("build")
        if build_details and isinstance(build_details, dict):
            build_details = build_details.copy()
        else:
            build_details = None

        return cls(
            name=data["name"],
            version=data.get("version", ""),
            build=data.get("build", {}).get("timestamp")
            if isinstance(data.get("build"), dict)
            else data.get("build"),
            date=data.get("date"),
            type=data.get("type", "solution"),
            parents=data.get("parents", []),
            categories=data.get("categories", []),
            license=data.get("license"),
            display=data.get("display"),
            build_details=build_details,
        )

    @classmethod
    def from_xml_file(cls, xml_path: str) -> "Product":
        """Create Product from XML file.

        Args:
            xml_path: Path to XML file.

        Returns:
            Product instance.

        Raises:
            FileNotFoundError: If XML file doesn't exist.
            ValueError: If XML is invalid.

        """
        xml_file = Path(xml_path)
        if not xml_file.exists():
            msg = f"XML file not found: {xml_path}"
            raise FileNotFoundError(msg)

        return cls.from_xml(xml_file.read_text(encoding="utf-8"))

    @classmethod
    def from_json_file(cls, json_path: str) -> "Product":
        """Create Product from JSON file.

        Args:
            json_path: Path to JSON file.

        Returns:
            Product instance.

        Raises:
            FileNotFoundError: If JSON file doesn't exist.
            ValueError: If JSON is invalid.

        """
        json_file = Path(json_path)
        if not json_file.exists():
            msg = f"JSON file not found: {json_path}"
            raise FileNotFoundError(msg)

        return cls.from_json(json_file.read_text(encoding="utf-8"))

    @classmethod
    def from_installer_folder(cls, folder_path: str) -> "Product":
        """Create Product from installer folder (XML + optional JSON).

        Args:
            folder_path: Path to product folder.

        Returns:
            Product instance with merged data.

        Raises:
            FileNotFoundError: If description.xml doesn't exist.
            ValueError: If XML is invalid.

        """
        folder = Path(folder_path)
        xml_path = folder / "description.xml"
        json_path = folder / "description.json"

        # Load XML (required)
        xml_product = cls.from_xml_file(str(xml_path))

        # Load JSON if exists (optional)
        if json_path.exists():
            json_product = cls.from_json_file(str(json_path))
            return cls.merge_xml_json(xml_product, json_product)

        return xml_product

    @classmethod
    def merge_xml_json(
        cls, xml_product: "Product", json_product: "Product"
    ) -> "Product":
        """Merge XML and JSON products, with JSON taking precedence.

        Args:
            xml_product: Product from XML.
            json_product: Product from JSON.

        Returns:
            Merged Product instance.

        Raises:
            ValueError: If product names don't match.

        """
        if xml_product.name != json_product.name:
            msg = (
                f"Product names don't match: {xml_product.name} != {json_product.name}"
            )
            raise ValueError(msg)

        # JSON takes precedence for common fields
        return cls(
            name=xml_product.name,
            version=json_product.version or xml_product.version,
            build=json_product.build or xml_product.build,
            date=json_product.date or xml_product.date,
            type=json_product.type or xml_product.type,
            parents=json_product.parents or xml_product.parents,
            categories=json_product.categories or xml_product.categories,
            license=json_product.license,
            display=json_product.display,
            build_details=json_product.build_details,
        )

    def to_xml(self) -> str:
        """Convert Product to XML string.

        Returns:
            XML string representation.

        """
        root = ET.Element("product")
        root.set("name", self.name)
        root.set("version", self.version)
        if self.build:
            root.set("build", self.build)
        if self.date:
            root.set("date", self.date)
        root.set("type", self.type)

        # Add parents
        if self.parents:
            parents_elem = ET.SubElement(root, "parents")
            for parent in self.parents:
                parent_elem = ET.SubElement(parents_elem, "parent")
                parent_elem.set("name", parent)

        # Add categories
        if self.categories:
            categories_elem = ET.SubElement(root, "categories")
            for category in self.categories:
                category_elem = ET.SubElement(categories_elem, "category")
                category_elem.set("name", category)

        return ET.tostring(root, encoding="unicode")

    def to_json(self) -> str:
        """Convert Product to JSON string.

        Returns:
            JSON string representation.

        """
        data = {
            "name": self.name,
            "version": self.version,
            "type": self.type,
            "parents": self.parents,
            "categories": self.categories,
        }

        if self.build:
            data["build"] = self.build
        if self.date:
            data["date"] = self.date
        if self.license:
            data["license"] = self.license
        if self.display:
            data["display"] = self.display
        if self.build_details:
            data["build"] = self.build_details

        return json.dumps(data, indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        """Return string representation of Product."""
        return (
            f"Product(name='{self.name}', version='{self.version}', type='{self.type}')"
        )

    def __repr__(self) -> str:
        """Detailed string representation of Product."""
        return (
            f"Product(name='{self.name}', version='{self.version}', "
            f"type='{self.type}', parents={self.parents}, categories={self.categories})"
        )
