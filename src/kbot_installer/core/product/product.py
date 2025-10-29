"""Product class for managing product definitions."""

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as defused_ET

from kbot_installer.core.provider import create_provider


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
    version: str = ""
    build: str | None = None
    date: str | None = None
    type: str = "solution"
    docs: list[str] = field(default_factory=list)
    env: Literal["dev", "prod"] = "dev"
    parents: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    license: str | None = None
    display: dict[str, Any] | None = None
    build_details: dict[str, Any] | None = None
    providers: list[str] = field(default_factory=lambda: ["nexus", "github", "bitbucket"])

    def __post_init__(self) -> None:
        self.provider = create_provider(name="selector", providers=self.providers)

    @staticmethod
    def _parse_comma_separated_string(value: str) -> list[str]:
        """Parse a comma-separated string into a list of trimmed strings.

        Args:
            value: Comma-separated string to parse.

        Returns:
            List of trimmed strings, empty list if value is empty or None.

        """
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _load_product_by_name(self, product_name: str) -> "Product":
        """Load a product by its name.

        Args:
            product_name: Name of the product to load.

        Returns:
            Product instance loaded from the provider.

        """
        # Create a minimal product instance with just the name
        # The provider will handle the actual loading
        return Product(name=product_name)

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

        # Extract doc (comma-separated string -> list)
        doc = cls._parse_comma_separated_string(root.get("doc", ""))

        return cls(
            name=name,
            version=version,
            build=build,
            date=date,
            type=product_type,
            parents=parents,
            categories=categories,
            docs=doc,
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
            docs=cls._parse_comma_separated_string(data.get("doc", "")),
            env=data.get("env", "dev"),
            license=data.get("license"),
            display=data.get("display"),
            build_details=build_details,
        )

    @classmethod
    def from_xml_file(cls, xml_path: Path) -> "Product":
        """Create Product from XML file.

        Args:
            xml_path: Path to XML file.

        Returns:
            Product instance.

        Raises:
            FileNotFoundError: If XML file doesn't exist.
            ValueError: If XML is invalid.

        """
        if not xml_path.exists():
            msg = f"XML file not found: {xml_path.name}"
            raise FileNotFoundError(msg)

        return cls.from_xml(xml_path.read_text(encoding="utf-8"))

    @classmethod
    def from_json_file(cls, json_path: Path) -> "Product":
        """Create Product from JSON file.

        Args:
            json_path: Path to JSON file.

        Returns:
            Product instance.

        Raises:
            FileNotFoundError: If JSON file doesn't exist.
            ValueError: If JSON is invalid.

        """
        if not json_path.exists():
            msg = f"JSON file not found: {json_path.name}"
            raise FileNotFoundError(msg)

        return cls.from_json(json_path.read_text(encoding="utf-8"))

    def load_from_installer_folder(self, folder_path: Path) -> None:
        """Load product data from installer folder (XML + optional JSON) into current instance.

        Args:
            folder_path: Path to product folder.

        Raises:
            FileNotFoundError: If description.xml doesn't exist.
            ValueError: If XML is invalid.

        """
        xml_path = folder_path / "description.xml"
        json_path = folder_path / "description.json"

        # Load XML (required)
        xml_product = self.from_xml_file(xml_path)

        # Load JSON if exists (optional)
        if json_path.exists():
            json_product = self.from_json_file(json_path)
            merged_product = self.merge_xml_json(xml_product, json_product)
            self._update_from_product(merged_product)
        else:
            self._update_from_product(xml_product)

    def _update_from_product(self, source_product: "Product") -> None:
        """Update current instance with data from another product.

        This method copies all relevant data from the source product to the current
        instance, preserving the original name and provider which should remain
        consistent with the instance's identity.

        Args:
            source_product: Product to copy data from.

        """
        self.version = source_product.version
        self.build = source_product.build
        self.date = source_product.date
        self.type = source_product.type
        self.docs = source_product.docs
        self.env = source_product.env
        self.parents = source_product.parents.copy()
        self.categories = source_product.categories.copy()
        self.license = source_product.license
        self.display = source_product.display
        self.build_details = source_product.build_details
        # Note: name and provider are not updated as they should remain consistent

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
            docs=json_product.docs or xml_product.docs,
            env=json_product.env or xml_product.env,
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

        # Add doc attribute (list -> comma-separated string)
        if self.docs:
            root.set("doc", ",".join(self.docs))

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
            "doc": ",".join(self.docs) if self.docs else "",
            "env": self.env,
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

    def clone(self, path: Path, *, dependencies: bool = True) -> None:
        """Clone the product to the given path using breadth-first traversal.

        Args:
            path: Path to clone the product to.
            dependencies: Whether to clone dependencies.

        """
        if not dependencies:
            self.provider.clone_and_checkout(path, self.version)
            self.load_from_installer_folder(path)
            return

        # BFS: Use a queue to process products level by level
        queue = deque([(self, path)])
        processed = set()  # Avoid processing the same product multiple times

        while queue:
            current_product, current_path = queue.popleft()

            # Skip if already processed
            if current_product.name in processed:
                continue

            # Clone current product
            current_product.provider.clone_and_checkout(current_path, current_product.version)
            current_product.load_from_installer_folder(current_path)
            processed.add(current_product.name)

            # Add dependencies to queue for next level
            for parent_name in current_product.parents:
                if parent_name not in processed:
                    parent_product = self._load_product_by_name(parent_name)
                    parent_path = current_path / parent_name
                    queue.append((parent_product, parent_path))

    def install(self, path: Path, *, dependencies: bool = True) -> None:
        """Install the product into the workarea.

        Args:
            path: Path to install the product to.
            dependencies: Whether to install dependencies.

        """
        msg = "Installation is not implemented yet"
        raise NotImplementedError(msg) from None

    def update(self, path: Path, *, dependencies: bool = True) -> None:
        """Update the product in the workarea.

        Args:
            path: Path to update the product from.
            dependencies: Whether to update dependencies.

        """
        msg = "Update is not implemented yet"
        raise NotImplementedError(msg) from None

    def uninstall(self, path: Path) -> None:
        """Uninstall the product from the workarea.

        Args:
            path: Path to uninstall the product from.

        """
        msg = "Uninstall is not implemented yet"
        raise NotImplementedError(msg) from None

    def repair(self, path: Path, *, dependencies: bool = True) -> None:
        """Repair the product in the workarea.

        Args:
            path: Path to repair the product from.
            dependencies: Whether to repair dependencies.

        """
        msg = "Repair is not implemented yet"
        raise NotImplementedError(msg) from None

    def upgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Upgrade the product in the workarea.

        Args:
            path: Path to upgrade the product from.
            dependencies: Whether to upgrade dependencies.

        """
        msg = "Upgrade is not implemented yet"
        raise NotImplementedError(msg) from None

    def downgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Downgrade the product in the workarea.

        Args:
            path: Path to downgrade the product from.
            dependencies: Whether to downgrade dependencies.

        """
        msg = "Downgrade is not implemented yet"
        raise NotImplementedError(msg) from None

    def backup(self, path: Path) -> None:
        """Backup the product in the given path.

        Args:
            path: Path to backup the product from.

        """
        msg = "Backup is not implemented yet"
        raise NotImplementedError(msg) from None

    def restore(self, path: Path) -> None:
        """Restore the product in the given path.

        Args:
            path: Path to restore the product from.

        """
        msg = "Restore is not implemented yet"
        raise NotImplementedError(msg) from None

    def delete(self, path: Path) -> None:
        """Delete the product in the given path.

        Args:
            path: Path to delete the product from.

        """
        msg = "Delete is not implemented yet"
        raise NotImplementedError(msg) from None

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
