"""InstallableProduct class for managing installable product definitions."""

import configparser
import contextlib
import fnmatch
import json
import shutil
import site
import sys
import tomllib
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

# Import here to avoid circular imports
from typing import Any, Literal

# xml.etree.ElementTree used only for XML creation (to_xml) - safe because we control the content
# XXE vulnerabilities only affect XML parsing/reading, not writing
from xml.etree import ElementTree as ET

from defusedxml import ElementTree as defused_ET

from kbot_installer.core.product.factory import create_installable
from kbot_installer.core.product.installable_base import InstallableBase
from kbot_installer.core.product.product_collection import ProductCollection
from kbot_installer.core.provider import create_provider
from kbot_installer.core.utils import ensure_directory


@dataclass
class InstallableProduct(InstallableBase):
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
    providers: list[str] = field(
        default_factory=lambda: ["nexus", "github", "bitbucket"]
    )
    dirname: Path | None = None  # Directory path where product is located

    def __post_init__(self) -> None:
        """Initialize provider after instance creation."""
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

    def _load_product_by_name(self, product_name: str) -> "InstallableProduct":
        """Load a product by its name.

        Args:
            product_name: Name of the product to load.

        Returns:
            Product instance loaded from the provider.

        """
        # Create a minimal product instance with just the name using factory
        # The provider will handle the actual loading
        return create_installable(name=product_name)

    @classmethod
    def from_xml(cls, xml_content: str) -> "InstallableProduct":
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
    def from_json(cls, json_content: str) -> "InstallableProduct":
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
    def from_xml_file(cls, xml_path: str | Path) -> "InstallableProduct":
        """Create Product from XML file.

        Args:
            xml_path: Path to XML file.

        Returns:
            Product instance.

        Raises:
            FileNotFoundError: If XML file doesn't exist.
            ValueError: If XML is invalid.

        """
        xml_path = Path(xml_path)
        if not xml_path.exists():
            msg = f"XML file not found: {xml_path.name}"
            raise FileNotFoundError(msg)

        return cls.from_xml(xml_path.read_text(encoding="utf-8"))

    @classmethod
    def from_json_file(cls, json_path: str | Path) -> "InstallableProduct":
        """Create Product from JSON file.

        Args:
            json_path: Path to JSON file.

        Returns:
            Product instance.

        Raises:
            FileNotFoundError: If JSON file doesn't exist.
            ValueError: If JSON is invalid.

        """
        json_path = Path(json_path)
        if not json_path.exists():
            msg = f"JSON file not found: {json_path.name}"
            raise FileNotFoundError(msg)

        return cls.from_json(json_path.read_text(encoding="utf-8"))

    @classmethod
    def from_installer_folder(cls, folder_path: Path) -> "InstallableProduct":
        """Create InstallableProduct from installer folder (XML + optional JSON).

        Args:
            folder_path: Path to product folder.

        Returns:
            InstallableProduct instance with merged data.

        Raises:
            FileNotFoundError: If description.xml doesn't exist.
            ValueError: If XML is invalid.

        """
        xml_path = folder_path / "description.xml"
        json_path = folder_path / "description.json"

        # Load XML (required)
        xml_product = cls.from_xml_file(xml_path)

        # Load JSON if exists (optional)
        if json_path.exists():
            json_product = cls.from_json_file(json_path)
            return cls.merge_xml_json(xml_product, json_product)

        return xml_product

    def load_from_installer_folder(self, folder_path: Path) -> None:
        """Load product data from installer folder (XML + optional JSON) into current instance.

        Args:
            folder_path: Path to product folder.

        Raises:
            FileNotFoundError: If description.xml doesn't exist.
            ValueError: If XML is invalid.

        """
        self.dirname = folder_path.resolve()
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

    def _update_from_product(self, source_product: "InstallableProduct") -> None:
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
        cls, xml_product: "InstallableProduct", json_product: "InstallableProduct"
    ) -> "InstallableProduct":
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

        # Use get_dependencies() to get BFS-ordered collection
        collection = self.get_dependencies()

        # Clone all products in BFS order
        for product in collection.products:
            product_path = (
                path.parent / product.name if product.name != self.name else path
            )
            product.provider.clone_and_checkout(product_path, product.version)
            product.load_from_installer_folder(product_path)

    def get_dependencies(self) -> "ProductCollection":
        """Get a ProductCollection containing this product and all its dependencies.

        Uses BFS traversal to collect all dependencies in the correct order.

        Returns:
            ProductCollection with BFS-ordered products.

        """
        # Collect all products using BFS
        queue = deque([self])
        processed = set()
        collected_products = []

        while queue:
            current_product = queue.popleft()

            if current_product.name in processed:
                continue

            collected_products.append(current_product)
            processed.add(current_product.name)

            # Add dependencies to queue
            for parent_name in current_product.parents:
                if parent_name not in processed:
                    parent_product = self._load_product_by_name(parent_name)
                    queue.append(parent_product)

        # Create ProductCollection with collected products
        return ProductCollection(collected_products)

    @property
    def pyproject_path(self) -> Path:
        """Get the path to pyproject.toml for this product.

        Returns:
            Path to pyproject.toml file.

        Raises:
            FileNotFoundError: If pyproject.toml doesn't exist or dirname is not set.

        """
        if not self.dirname:
            msg = f"Product {self.name} has no dirname set"
            raise FileNotFoundError(msg)

        pyproject_file = self.dirname / "pyproject.toml"
        if not pyproject_file.exists():
            msg = f"pyproject.toml not found in {self.dirname}"
            raise FileNotFoundError(msg)

        return pyproject_file

    def get_kconf(self, product: str | None = None) -> dict[str, Any]:
        """Get kbot.conf configuration for product and all dependencies.

        Aggregates kbot.conf files from the current product and all its dependencies
        using BFS traversal. Returns a structure with:
        - "aggregated": merged configuration from all products
        - "{product_name}": configuration for each specific product

        Args:
            product: Optional product name. If None, uses current product.

        Returns:
            Dictionary with aggregated config and per-product configs.

        """
        # Determine target product
        target_product = self
        if product:
            collection = self.get_dependencies()
            found_product = collection.get_product(product)
            if not found_product:
                msg = f"Product {product} not found in dependencies"
                raise ValueError(msg)
            target_product = found_product

        # Get all products in BFS order
        collection = target_product.get_dependencies()
        result: dict[str, Any] = {"aggregated": {}}

        # Load kbot.conf from each product
        for prod in collection.products:
            if not prod.dirname:
                continue

            conf_path = prod.dirname / "conf" / "kbot.conf"
            if not conf_path.exists():
                result[prod.name] = {}
                continue

            # Parse INI-style config file
            parser = configparser.ConfigParser()
            try:
                parser.read(conf_path, encoding="utf-8")
            except configparser.Error:
                result[prod.name] = {}
                continue

            # Convert to dict
            prod_config: dict[str, Any] = {}
            for section in parser.sections():
                prod_config[section] = dict(parser[section])

            result[prod.name] = prod_config

            # Aggregate into merged config
            for section, values in prod_config.items():
                if section not in result["aggregated"]:
                    result["aggregated"][section] = {}
                # Last product wins for same keys (BFS order ensures correct precedence)
                result["aggregated"][section].update(values)

        return result

    def _is_path_ignored(  # noqa: C901, PLR0912
        self,
        file_path: Path,
        workarea_root: Path,
        ignore_patterns: dict[str, list[str]],
        source_dir_path: Path | None = None,
    ) -> bool:
        """Check if a file path should be ignored based on ignore patterns.

        Args:
            file_path: Path to check (can be source file or workarea file).
            workarea_root: Root of the workarea.
            ignore_patterns: Dict mapping source dirs to list of ignore patterns.
            source_dir_path: Optional source directory path to calculate relative path.

        Returns:
            True if path should be ignored.

        """
        # Check each source directory's ignore patterns
        for source_dir, patterns in ignore_patterns.items():
            # Calculate relative path from source directory
            rel_to_source: Path | None = None

            if source_dir_path:
                # For source files, calculate relative to source_dir_path / source_dir
                source_base = source_dir_path / source_dir
                try:
                    rel_to_source = file_path.relative_to(source_base)
                except ValueError:
                    # Try relative to source_dir_path
                    try:
                        rel = file_path.relative_to(source_dir_path)
                        # Check if it starts with source_dir
                        if source_dir != "." and not str(rel).startswith(
                            source_dir + "/"
                        ):
                            continue
                        # Extract part after source_dir
                        if source_dir != ".":
                            parts = str(rel).split("/", 1)
                            if len(parts) > 1 and parts[0] == source_dir:
                                rel_to_source = Path(parts[1])
                            else:
                                continue
                        else:
                            rel_to_source = rel
                    except ValueError:
                        continue
            else:
                # For workarea files, calculate relative to workarea_root
                try:
                    rel_path = file_path.relative_to(workarea_root)
                    if source_dir != "." and not rel_path.is_relative_to(source_dir):
                        continue
                    rel_to_source = (
                        rel_path.relative_to(source_dir)
                        if source_dir != "."
                        else rel_path
                    )
                except ValueError:
                    continue

            if rel_to_source is None:
                continue

            for pattern in patterns:
                # Match against relative path
                rel_str = str(rel_to_source)
                # Check full path
                if fnmatch.fnmatch(rel_str, pattern):
                    return True
                # Check just the name
                if fnmatch.fnmatch(rel_to_source.name, pattern):
                    return True
                # Check any component in the path
                if "/" in rel_str or "\\" in rel_str:
                    parts = rel_str.replace("\\", "/").split("/")
                    if any(fnmatch.fnmatch(part, pattern) for part in parts):
                        return True

        return False

    def _is_destination_taken(self, dest_path: Path, processed: set[Path]) -> bool:
        """Check if a destination path is already processed (first-come-first-served).

        Also checks if any parent directory is already processed (for directories).

        Args:
            dest_path: Destination path to check.
            processed: Set of already processed destination paths.

        Returns:
            True if destination is already taken.

        """
        dest_resolved = dest_path.resolve()

        # Check exact match
        if dest_resolved in processed:
            return True

        # Check if any parent is in processed (directory case)
        for processed_path in processed:
            with contextlib.suppress(ValueError):
                dest_resolved.relative_to(processed_path.resolve())
                return True

        # Check if dest is a parent of any processed path
        for processed_path in processed:
            with contextlib.suppress(ValueError):
                processed_path.resolve().relative_to(dest_resolved)
                return True

        return False

    def _handle_work_init(
        self,
        workarea_root: Path,
        init_config: dict[str, list[str]],
        processed: set[Path],
    ) -> None:
        """Handle work.init section - create directories and files.

        Args:
            workarea_root: Root of the workarea.
            init_config: Dict mapping base directories to lists of items to create.
            processed: Set to track processed paths.

        """
        for base_dir, items in init_config.items():
            base_path = workarea_root / base_dir
            ensure_directory(base_path)

            for item in items:
                item_path = base_path / item

                if not self._is_destination_taken(item_path, processed):
                    if item_path.suffix:  # Has extension, assume it's a file
                        item_path.parent.mkdir(parents=True, exist_ok=True)
                        if not item_path.exists():
                            item_path.touch()
                    else:  # Assume it's a directory
                        ensure_directory(item_path)

                    processed.add(item_path.resolve())

    def _handle_work_copy(  # noqa: C901, PLR0912
        self,
        workarea_root: Path,
        product_dir: Path,
        copy_config: dict[str, list[str]],
        ignore_patterns: dict[str, list[str]],
        processed: set[Path],
    ) -> None:
        """Handle work.copy section - copy files matching patterns.

        Args:
            workarea_root: Root of the workarea.
            product_dir: Directory of the product being processed.
            copy_config: Dict mapping source dirs to lists of file patterns.
            ignore_patterns: Patterns to ignore.
            processed: Set to track processed paths.

        """
        for source_dir, patterns in copy_config.items():
            source_path = product_dir / source_dir
            if not source_path.exists():
                continue

            dest_base = workarea_root / source_dir

            # If patterns is empty, copy everything
            if not patterns:
                if (
                    not self._is_destination_taken(dest_base, processed)
                    and source_path.is_file()
                ):
                    dest_base.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_base)
                    processed.add(dest_base.resolve())
                elif (
                    not self._is_destination_taken(dest_base, processed)
                    and source_path.is_dir()
                ):
                    if dest_base.exists():
                        shutil.rmtree(dest_base)
                    shutil.copytree(source_path, dest_base, dirs_exist_ok=True)
                    processed.add(dest_base.resolve())
                continue

            # Process patterns
            for pattern in patterns:
                # Use rglob to find matching files
                if source_path.is_file():
                    files = (
                        [source_path]
                        if fnmatch.fnmatch(source_path.name, pattern)
                        else []
                    )
                else:
                    files = list(source_path.rglob(pattern))

                for src_file in files:
                    if not src_file.is_file():
                        continue

                    # Check ignore patterns
                    if self._is_path_ignored(
                        src_file, workarea_root, ignore_patterns, product_dir
                    ):
                        continue

                    # Calculate relative path from source_dir
                    try:
                        rel_path = src_file.relative_to(source_path)
                    except ValueError:
                        rel_path = Path(src_file.name)

                    dest_file = dest_base / rel_path

                    if self._is_destination_taken(dest_file, processed):
                        continue

                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    processed.add(dest_file.resolve())

    def _handle_work_link(  # noqa: C901, PLR0912
        self,
        workarea_root: Path,
        product_dir: Path,
        link_config: dict[str, list[str]],
        ignore_patterns: dict[str, list[str]],
        processed: set[Path],
    ) -> None:
        """Handle work.link section - create symlinks for files matching patterns.

        Args:
            workarea_root: Root of the workarea.
            product_dir: Directory of the product being processed.
            link_config: Dict mapping source dirs to lists of file patterns.
            ignore_patterns: Patterns to ignore.
            processed: Set to track processed paths.

        """
        for source_dir, patterns in link_config.items():
            source_path = product_dir / source_dir
            if not source_path.exists():
                continue

            dest_base = workarea_root / source_dir

            # If patterns is empty, link everything
            if not patterns:
                if (
                    not self._is_destination_taken(dest_base, processed)
                    and source_path.is_file()
                ):
                    dest_base.parent.mkdir(parents=True, exist_ok=True)
                    if dest_base.exists() and not dest_base.is_symlink():
                        dest_base.unlink(missing_ok=True)
                    if not dest_base.exists():
                        dest_base.symlink_to(source_path.resolve())
                    processed.add(dest_base.resolve())
                elif (
                    not self._is_destination_taken(dest_base, processed)
                    and source_path.is_dir()
                ):
                    # Link the directory itself
                    if dest_base.exists() and dest_base.is_symlink():
                        dest_base.unlink()
                    elif dest_base.exists():
                        # If it's not a symlink, it's already been processed
                        processed.add(dest_base.resolve())
                        continue

                    dest_base.parent.mkdir(parents=True, exist_ok=True)
                    dest_base.symlink_to(source_path.resolve())
                    processed.add(dest_base.resolve())
                continue

            # Process patterns
            for pattern in patterns:
                # Use rglob to find matching files
                if source_path.is_file():
                    files = (
                        [source_path]
                        if fnmatch.fnmatch(source_path.name, pattern)
                        else []
                    )
                else:
                    files = list(source_path.rglob(pattern))

                for src_file in files:
                    # Check ignore patterns
                    if self._is_path_ignored(
                        src_file, workarea_root, ignore_patterns, product_dir
                    ):
                        continue

                    # Calculate relative path from source_dir
                    try:
                        rel_path = src_file.relative_to(source_path)
                    except ValueError:
                        rel_path = Path(src_file.name)

                    dest_file = dest_base / rel_path

                    if self._is_destination_taken(dest_file, processed):
                        continue

                    # Create symlink
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if dest_file.exists() and dest_file.is_symlink():
                        dest_file.unlink()
                    elif dest_file.exists():
                        # Already exists and not a symlink - skip
                        processed.add(dest_file.resolve())
                        continue

                    # Create symlink from source to destination
                    dest_file.symlink_to(src_file.resolve())
                    processed.add(dest_file.resolve())

    def _handle_work_link_external(
        self,
        workarea_root: Path,
        external_config: dict[str, str],
        processed: set[Path],
    ) -> None:
        """Handle work.link.external section - link files from site-packages.

        Args:
            workarea_root: Root of the workarea.
            external_config: Dict mapping source paths in site-packages to dest paths.
            processed: Set to track processed paths.

        """
        # Get site-packages directory
        try:
            site_packages = site.getsitepackages()[0]
        except (IndexError, AttributeError):
            # Fallback for virtualenv or custom Python installations
            site_packages = next(
                (Path(p) for p in sys.path if "site-packages" in p), Path.cwd()
            )

        site_packages_path = Path(site_packages)

        for source_rel, dest_rel in external_config.items():
            source_path = site_packages_path / source_rel
            if not source_path.exists():
                continue

            dest_path = workarea_root / dest_rel

            if self._is_destination_taken(dest_path, processed):
                continue

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if dest_path.exists() and dest_path.is_symlink():
                dest_path.unlink()
            elif dest_path.exists():
                # Already exists and not a symlink - skip
                processed.add(dest_path.resolve())
                continue

            # Create symlink from site-packages source to workarea destination
            dest_path.symlink_to(source_path.resolve())
            processed.add(dest_path.resolve())

    def install(self, path: Path, *, dependencies: bool = True) -> None:  # noqa: C901, PLR0912
        """Install the product into the workarea.

        Extracts the [work] section from pyproject.toml for this product and all
        dependencies (if enabled), and assembles the workarea according to the
        configuration. Handles work.init, work.copy, work.link, and work.link.external
        sections in that order.

        Args:
            path: Path to install the product to (workarea root).
            dependencies: Whether to install dependencies.

        """
        ensure_directory(path)

        # Get products to process (BFS order)
        if dependencies:
            collection = self.get_dependencies()
            products = collection.products
        else:
            products = [self]

        # Track processed destinations (first-come-first-served)
        processed: set[Path] = set()

        # Process each product in BFS order
        for product in products:
            if not product.dirname:
                continue

            try:
                pyproject_file = product.pyproject_path
            except FileNotFoundError:
                # Skip products without pyproject.toml
                continue

            # Load pyproject.toml
            try:
                with pyproject_file.open("rb") as f:
                    pyproject_data = tomllib.load(f)
            except (OSError, tomllib.TOMLDecodeError):
                continue

            work_config = pyproject_data.get("work", {})
            if not work_config:
                continue

            # Extract sections
            init_config = work_config.get("init", {})
            copy_config = work_config.get("copy", {})
            ignore_config = work_config.get("ignore", {})
            link_config = work_config.get("link", {})
            link_section = work_config.get("link", {})
            if isinstance(link_section, dict):
                link_external_config = link_section.get("external", {})
            else:
                link_external_config = {}

            # Process in order: init, copy, link, link.external
            if init_config:
                self._handle_work_init(path, init_config, processed)

            if copy_config:
                self._handle_work_copy(
                    path, product.dirname, copy_config, ignore_config, processed
                )

            if link_config:
                self._handle_work_link(
                    path, product.dirname, link_config, ignore_config, processed
                )

            if link_external_config:
                self._handle_work_link_external(path, link_external_config, processed)

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
        """Return string representation of InstallableProduct."""
        return f"InstallableProduct(name='{self.name}', version='{self.version}', type='{self.type}')"

    def __repr__(self) -> str:
        """Detailed string representation of InstallableProduct."""
        return (
            f"InstallableProduct(name='{self.name}', version='{self.version}', "
            f"type='{self.type}', parents={self.parents}, categories={self.categories})"
        )
