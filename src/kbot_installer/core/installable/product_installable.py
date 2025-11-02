"""ProductInstallable class for managing installable product definitions."""

import configparser
import contextlib
import fnmatch
import importlib
import json
import logging
import os
import shutil
import site
import sys
import tomllib
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict

from kbot_installer.core.installable.factory import create_installable
from kbot_installer.core.installable.installable_base import InstallableBase
from kbot_installer.core.installable.product_collection import ProductCollection
from kbot_installer.core.provider import create_provider
from kbot_installer.core.utils import ensure_directory, version_to_branch

logger = logging.getLogger(__name__)

# Type alias for product configuration (INI-style: section -> option -> value)
ProductConfig = dict[str, dict[str, str]]

# Result type for get_kconf(): contains "aggregated" key and per-product configs
# Structure: {"aggregated": ProductConfig, product_name: ProductConfig, ...}
KbotConfigResult = dict[str, ProductConfig]


class BuildDetails(TypedDict, total=False):
    """Build details structure.

    Attributes:
        timestamp: Build timestamp (e.g., "2025/09/29 14:08:06").
        branch: Git branch name (e.g., "release-2025.03-dev").
        commit: Git commit hash (e.g., "7062432bd6ebeb174bf38bc5dde8d75d6e603e09").

    """

    timestamp: str
    branch: str
    commit: str


@dataclass
class ProductInstallable(InstallableBase):
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
        branch: Specific branch to use (overrides version_to_branch calculation).
               If specified, env is forced to "dev".

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
    # Multilingual info: {"name": {"en": "...", "fr": "..."}, ...}
    display: dict[str, dict[str, str]] | None = None
    build_details: BuildDetails | None = None
    providers: list[str] = field(
        default_factory=lambda: ["nexus", "github", "bitbucket"]
    )
    # Directory path where product is located
    dirname: Path | None = None
    # Provider name that was successfully used during clone
    provider_name_used: str | None = None
    # Branch that was successfully used during clone
    branch_used: str | None = None
    # Specific branch to use (overrides version_to_branch calculation)
    branch: str | None = None

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

    def _load_product_by_name(
        self,
        product_name: str,
        base_path: Path | None = None,
        default_version: str | None = None,
    ) -> InstallableBase:
        """Load a product by its name.

        Args:
            product_name: Name of the product to load.
            base_path: Optional base path where cloned products are located.
                      If provided and product exists, load from cloned repo.
            default_version: Optional default version to use if product doesn't have one.
                           Typically the version of the parent product.

        Returns:
            Product instance loaded from the provider or cloned repo.

        """
        # Use the same providers as the parent product to ensure consistency
        providers = self.providers
        # Use default_version if provided, otherwise use parent's version as fallback
        version = default_version or self.version
        # Use the same branch as the parent product if specified
        branch = self.branch

        # Try to load from cloned repository if base_path is provided
        if base_path:
            cloned_product_path = base_path / product_name
            if (cloned_product_path / "description.xml").exists():
                product = create_installable(
                    name=product_name,
                    providers=providers,
                    version=version,
                    branch=branch,
                )
                product.load_from_installer_folder(cloned_product_path)
                # If description.xml doesn't specify a version, keep the default version
                if not product.version and version:
                    product.version = version
                return product

        # Otherwise, create a minimal product instance with just the name using factory
        # The provider will handle the actual loading when cloning
        # Pass providers, version, and branch to ensure dependencies use the same as the main product
        return create_installable(
            name=product_name, providers=providers, version=version, branch=branch
        )

    @classmethod
    def from_xml(cls, xml_content: str) -> InstallableBase:
        """Create Product from XML content.

        Args:
            xml_content: XML string content.

        Returns:
            Product instance.

        Raises:
            ValueError: If XML is invalid or missing required fields.

        """
        # Import defusedxml locally to avoid heavy import at module level
        from defusedxml import ElementTree as defused_ET  # noqa: PLC0415

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

        # Get version - if attribute doesn't exist or is empty, use empty string
        # This allows us to distinguish between "no version specified" vs "version explicitly set"
        version = root.get("version") or ""
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
    def from_json(cls, json_content: str) -> InstallableBase:
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
    def from_xml_file(cls, xml_path: str | Path) -> InstallableBase:
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
    def from_json_file(cls, json_path: str | Path) -> InstallableBase:
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
    def from_installer_folder(cls, folder_path: Path) -> InstallableBase:
        """Create ProductInstallable from installer folder (XML + optional JSON).

        Args:
            folder_path: Path to product folder.

        Returns:
            ProductInstallable instance with merged data.

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

    def _update_from_product(self, source_product: InstallableBase) -> None:
        """Update current instance with data from another product.

        This method copies all relevant data from the source product to the current
        instance, preserving the original name and provider which should remain
        consistent with the instance's identity.

        Args:
            source_product: Product to copy data from.

        """
        # Only update version if source has a non-empty version
        # This preserves the version that was set before loading (e.g., inherited from parent)
        if source_product.version:
            self.version = source_product.version
        # If source version is empty but we have a version, keep ours (inherited from parent)
        # This happens when description.xml has version="" - we want to keep parent's version
        # Preserve branch: only update if source has an explicit branch, otherwise keep ours
        # This ensures branch inherited from parent is not lost when loading from XML
        if hasattr(source_product, "branch") and source_product.branch is not None:
            self.branch = source_product.branch
        # If source doesn't have branch or has None, self.branch remains unchanged
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
        # Note: name, provider, and branch are preserved as they should remain consistent

    @classmethod
    def merge_xml_json(
        cls, xml_product: InstallableBase, json_product: InstallableBase
    ) -> InstallableBase:
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
        # Preserve branch from either product if it exists (not stored in XML/JSON typically)
        branch = None
        if hasattr(json_product, "branch") and json_product.branch:
            branch = json_product.branch
        elif hasattr(xml_product, "branch") and xml_product.branch:
            branch = xml_product.branch

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
            branch=branch,
        )

    def to_xml(self) -> str:
        """Convert Product to XML string.

        Returns:
            XML string representation.

        """
        # Access underlying ElementTree for creation (safe - we control the content)
        # defusedxml wraps xml.etree.ElementTree for secure parsing, but creation is safe
        # __origin__ contains the string 'xml.etree.ElementTree', so we import it dynamically
        from defusedxml import ElementTree as defused_ET  # noqa: PLC0415

        _etree_module_name = defused_ET.__origin__  # type: ignore[attr-defined]
        ET = importlib.import_module(_etree_module_name)  # noqa: N806

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
        """Convert Product to JSON dictionary.

        Returns:
            JSON dictionary.

        """
        return {
            "name": self.name,
            "version": self.version,
            "build": self.build,
            "date": self.date,
            "type": self.type,
            "parents": self.parents,
            "categories": self.categories,
            "doc": ",".join(self.docs) if self.docs else None,
            "env": self.env,
            "license": self.license,
            "display": self.display,
            "build_details": self.build_details,
            "provider_name_used": self.provider_name_used,
            "branch_used": self.branch_used,
            "branch": self.branch,
        }

    def clone(self, path: Path, *, dependencies: bool = True) -> None:
        """Clone the product to the given path using breadth-first traversal.

        Args:
            path: Path to the directory that will contain the cloned products.
            dependencies: Whether to clone dependencies.

        """
        # Ensure the base path exists
        path.mkdir(parents=True, exist_ok=True)

        # Use specified branch if provided, otherwise convert version to branch name
        # Store the calculated branch in self.branch so it's preserved and can be used by dependencies
        if not self.branch and self.version:
            self.branch = version_to_branch(self.version, env=self.env)
        branch = self.branch

        if not dependencies:
            logger.warning("Cloning %s (branch: %s) to %s", self.name, branch, path)
            product_path = path / self.name
            self.provider.clone_and_checkout(
                product_path, branch, repository_name=self.name
            )
            # Store the provider and branch used (providers update these during clone)
            self.provider_name_used = self.provider.get_name()
            self.branch_used = self.provider.get_branch()
            # Only load if description.xml exists (clone may have failed)
            if (product_path / "description.xml").exists():
                self.load_from_installer_folder(product_path)
            # Export single product collection to lock file
            collection = ProductCollection([self])
            lock_file = path / "products.lock.json"
            collection.export_to_json(str(lock_file))
            logger.info("Exported product collection to %s", lock_file)
            return

        # First, clone the main product to get its dependencies
        main_product_path = path / self.name
        self.provider.clone_and_checkout(
            main_product_path, branch, repository_name=self.name
        )
        # Store the provider and branch used (providers update these during clone)
        self.provider_name_used = self.provider.get_name()
        self.branch_used = self.provider.get_branch()
        # Load the main product to get its parents (dependencies)
        if (main_product_path / "description.xml").exists():
            self.load_from_installer_folder(main_product_path)
            # Ensure dirname is set after loading
            if not self.dirname:
                self.dirname = main_product_path.resolve()

        # Use iterative BFS approach: clone products progressively and discover
        # new dependencies as we load each cloned product's description.xml
        # This ensures we discover all transitive dependencies even if intermediate
        # products weren't known initially
        processed = set()
        queue = deque([self])

        while queue:
            current_product = queue.popleft()

            # Skip if already processed (can happen if product appears in multiple dependency chains)
            if current_product.name in processed:
                continue

            # Clone current product if not already cloned (main product is already cloned)
            if current_product.name != self.name and not self._clone_dependency_product(
                current_product, path, processed
            ):
                continue

            # Mark as processed
            processed.add(current_product.name)

            # Discover new dependencies from the (now loaded) current product
            self._discover_and_queue_parents(current_product, queue, processed, path)

        # Now get the final collection with all discovered products
        # All products are now cloned, so get_dependencies will load them all properly
        collection = self.get_dependencies(base_path=path)

        # Export collection to products.lock.json for install() to use later
        lock_file = path / "products.lock.json"
        collection.export_to_json(str(lock_file))
        logger.info("Exported product collection to %s", lock_file)

    def _clone_dependency_product(
        self, product: InstallableBase, base_path: Path, processed: set[str]
    ) -> bool:
        """Clone a dependency product.

        Args:
            product: Product to clone.
            base_path: Base path for cloning.
            processed: Set of processed product names.

        Returns:
            True if clone was successful, False otherwise.

        """
        # Use specified branch if provided, otherwise convert version to branch name
        # Store the calculated branch in product.branch so it's preserved
        if not product.branch and product.version:
            product.branch = version_to_branch(product.version, env=product.env)
        dependency_branch = product.branch
        product_path = base_path / product.name

        try:
            # Clone with branch fallback handled by selector_provider using config.branches
            product.provider.clone_and_checkout(
                product_path,
                dependency_branch,
                repository_name=product.name,
            )
            # Store the provider and branch used (providers update these during clone)
            product.provider_name_used = product.provider.get_name()
            product.branch_used = product.provider.get_branch()
        except Exception:
            # Clone failed - selector_provider already tried all fallback branches from config
            logger.exception("Failed to clone %s", product.name)
            # Mark as processed even if clone failed to avoid infinite loop
            processed.add(product.name)
            # Continue with other dependencies even if one fails
            return False

        # Only load if description.xml exists (clone may have failed)
        if (product_path / "description.xml").exists():
            product.load_from_installer_folder(product_path)
            # Ensure dirname is set after loading
            if not product.dirname:
                product.dirname = product_path.resolve()
        return True

    def _discover_and_queue_parents(
        self,
        current_product: InstallableBase,
        queue: deque,
        processed: set[str],
        base_path: Path,
    ) -> None:
        """Discover and queue parent products for cloning.

        Args:
            current_product: Current product being processed.
            queue: Queue of products to process.
            processed: Set of processed product names.
            base_path: Base path where products are cloned.

        """
        # Process parents if:
        # 1. Product is the main product (already cloned and loaded), or
        # 2. Product was successfully cloned and loaded (has dirname and description.xml)
        should_process_parents = False
        if current_product.name == self.name:
            # Main product: should have been loaded already
            should_process_parents = True
        elif (
            current_product.dirname
            and (current_product.dirname / "description.xml").exists()
        ):
            # Cloned product: verify it was successfully loaded
            should_process_parents = True

        if should_process_parents:
            for parent_name in current_product.parents:
                if parent_name not in processed:
                    # Load parent product - try from cloned repo first, otherwise create minimal instance
                    parent_product = self._load_product_by_name(
                        parent_name,
                        base_path=base_path,
                        default_version=current_product.version,
                    )
                    queue.append(parent_product)

    def get_dependencies(self, base_path: Path | None = None) -> ProductCollection:
        """Get a ProductCollection containing this product and all its dependencies.

        Uses BFS traversal to collect all dependencies in the correct order.

        Args:
            base_path: Optional base path where cloned products are located.
                      If provided, dependencies will be loaded from cloned repos if available.

        Returns:
            ProductCollection with BFS-ordered products.

        """
        # Collect all products using BFS
        queue = deque([self])
        processed = set[str]()
        collected_products = []

        while queue:
            current_product = queue.popleft()

            if current_product.name in processed:
                continue

            collected_products.append(current_product)
            processed.add(current_product.name)

            # Add dependencies to queue
            # Pass current product's version as default so dependencies inherit it
            for parent_name in current_product.parents:
                if parent_name not in processed:
                    parent_product = self._load_product_by_name(
                        parent_name,
                        base_path=base_path,
                        default_version=current_product.version,
                    )
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

    def get_kconf(self, product: str | None = None) -> KbotConfigResult:
        """Get kbot.conf configuration for product and all dependencies.

        Aggregates kbot.conf files from the current product and all its dependencies
        using BFS traversal. Returns a structure with:
        - "aggregated": merged configuration from all products
        - "{product_name}": configuration for each specific product

        Args:
            product: Optional product name. If None, uses current product.

        Returns:
            Dictionary with aggregated config and per-product configs.
            Structure: {"aggregated": ProductConfig, product_name: ProductConfig, ...}
            where ProductConfig is dict[str, dict[str, str]] (section -> option -> value).

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
        result: KbotConfigResult = {"aggregated": {}}

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
            prod_config: ProductConfig = {}
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

    def _handle_work_link(  # noqa: C901, PLR0912, PLR0915
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

            # Process patterns - optimized to avoid rglob slowness
            # Collect all files matching patterns in one pass
            files_to_link: list[tuple[Path, Path]] = []  # (src_file, dest_file)
            created_dirs: set[Path] = set()  # Cache created directories
            resolved_src_cache: dict[Path, Path] = {}  # Cache resolve() calls

            for pattern in patterns:
                if source_path.is_file():
                    if fnmatch.fnmatch(source_path.name, pattern):
                        files_to_link.append(
                            (source_path, dest_base / source_path.name)
                        )
                    continue

                # Optimized recursive file finding - walk once and filter
                # This is much faster than rglob(pattern) which traverses everything
                for root, dirs, filenames in os.walk(source_path):
                    root_path = Path(root)
                    # Check ignore patterns for directories early
                    if self._is_path_ignored(
                        root_path, workarea_root, ignore_patterns, product_dir
                    ):
                        # Remove ignored dirs from walk
                        dirs[:] = []
                        continue

                    for filename in filenames:
                        file_path = root_path / filename
                        # Match pattern
                        if not fnmatch.fnmatch(filename, pattern):
                            continue

                        # Check ignore patterns
                        if self._is_path_ignored(
                            file_path, workarea_root, ignore_patterns, product_dir
                        ):
                            continue

                        # Calculate relative path and destination
                        try:
                            rel_path = file_path.relative_to(source_path)
                        except ValueError:
                            rel_path = Path(filename)

                        dest_file = dest_base / rel_path

                        # Check if destination is taken (early exit)
                        if self._is_destination_taken(dest_file, processed):
                            continue

                        files_to_link.append((file_path, dest_file))

            # Process all files in batch (already filtered and validated)
            for src_file, dest_file in files_to_link:
                # Ensure parent directory exists (cache to avoid repeated mkdir)
                dest_parent = dest_file.parent
                if dest_parent not in created_dirs:
                    dest_parent.mkdir(parents=True, exist_ok=True)
                    created_dirs.add(dest_parent)

                # Check destination status (optimized)
                if dest_file.exists():
                    if dest_file.is_symlink():
                        dest_file.unlink()
                    else:
                        # Already exists and not a symlink - skip
                        dest_resolved = dest_file.resolve()
                        processed.add(dest_resolved)
                        continue

                # Cache resolve() calls
                if src_file not in resolved_src_cache:
                    resolved_src_cache[src_file] = src_file.resolve()

                # Create symlink
                dest_file.symlink_to(resolved_src_cache[src_file])
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

    def _find_lock_file(
        self, path: Path, installer_path: Path | None
    ) -> tuple[Path | None, Path | None]:
        """Find products.lock.json file in common locations.

        Args:
            path: Workarea path.
            installer_path: Optional installer path.

        Returns:
            Tuple of (lock_file_path, effective_installer_path).

        """
        if installer_path:
            return installer_path / "products.lock.json", installer_path

        potential_lock = path / "products.lock.json"
        if potential_lock.exists():
            return potential_lock, path

        parent_lock = path.parent / "products.lock.json"
        if parent_lock.exists():
            return parent_lock, path.parent

        return None, None

    def _verify_products_from_lock(
        self, collection: ProductCollection, installer_path: Path
    ) -> bool:
        """Verify all products in collection exist in installer.

        Args:
            collection: Product collection from lock file.
            installer_path: Path to installer directory.

        Returns:
            True if all products exist, False otherwise.

        """
        for product in collection.products:
            if not product.dirname or not product.dirname.exists():
                potential_dir = installer_path / product.name
                if (potential_dir / "description.xml").exists():
                    product.dirname = potential_dir.resolve()
                else:
                    logger.warning(
                        "Product %s from lock file not found in installer at %s",
                        product.name,
                        potential_dir,
                    )
                    return False
        return True

    def _load_products_from_lock(
        self, lock_file: Path, installer_path: Path, *, dependencies: bool
    ) -> list[InstallableBase]:
        """Load products from lock file.

        Args:
            lock_file: Path to products.lock.json.
            installer_path: Path to installer directory.
            dependencies: Whether to include dependencies.

        Returns:
            List of products, empty if lock file invalid.

        """
        try:
            collection = ProductCollection.from_json(lock_file)
            if not self._verify_products_from_lock(collection, installer_path):
                logger.warning(
                    "Installer incomplete, missing products. Will clone if needed."
                )
                return []

            products = collection.products
            if not dependencies:
                products = [p for p in products if p.name == self.name]
            logger.info("Installer already complete, using products.lock.json")
        except (FileNotFoundError, ValueError) as e:
            logger.warning("Failed to load products.lock.json: %s", e)
            products = []
        else:
            return products
        return []

    def _ensure_installer_complete(
        self,
        installer_path: Path,
        *,
        dependencies: bool,
    ) -> list[InstallableBase]:
        """Ensure installer is complete, cloning if needed.

        Args:
            installer_path: Path to installer directory.
            dependencies: Whether to clone dependencies.

        Returns:
            List of products from lock file after cloning.

        """
        logger.info("Installer not complete, cloning products to %s", installer_path)
        self.clone(installer_path, dependencies=dependencies)

        lock_file = installer_path / "products.lock.json"
        if lock_file.exists():
            return self._load_products_from_lock(
                lock_file, installer_path, dependencies=dependencies
            )
        return []

    def _process_product_work_config(
        self,
        product: InstallableBase,
        workarea_root: Path,
        processed: set[Path],
    ) -> None:
        """Process work configuration for a single product.

        Args:
            product: Product to process.
            workarea_root: Root of workarea.
            processed: Set of processed paths.

        """
        try:
            pyproject_file = product.pyproject_path
        except FileNotFoundError:
            logger.warning("Product %s has no pyproject.toml", product.name)
            return

        try:
            with pyproject_file.open("rb") as f:
                pyproject_data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            logger.warning("Failed to load pyproject.toml for product %s", product.name)
            return

        work_config = pyproject_data.get("work", {})
        if not work_config:
            return

        init_config = work_config.get("init", {})
        copy_config = work_config.get("copy", {})
        ignore_config = work_config.get("ignore", {})
        link_config = work_config.get("link", {})
        link_section = work_config.get("link", {})
        link_external_config = (
            link_section.get("external", {}) if isinstance(link_section, dict) else {}
        )

        if init_config:
            logger.warning("Processing init section for product %s", product.name)
            self._handle_work_init(workarea_root, init_config, processed)

        if copy_config:
            logger.warning("Processing copy section for product %s", product.name)
            self._handle_work_copy(
                workarea_root, product.dirname, copy_config, ignore_config, processed
            )

        if link_config:
            logger.warning("Processing link section for product %s", product.name)
            self._handle_work_link(
                workarea_root, product.dirname, link_config, ignore_config, processed
            )

        if link_external_config:
            logger.warning(
                "Processing link.external section for product %s", product.name
            )
            self._handle_work_link_external(
                workarea_root, link_external_config, processed
            )

    def install(
        self,
        path: Path,
        *,
        dependencies: bool = True,
        installer_path: Path | None = None,
    ) -> None:
        """Install the product into the workarea.

        Extracts the [work] section from pyproject.toml for this product and all
        dependencies (if enabled), and assembles the workarea according to the
        configuration. Handles work.init, work.copy, work.link, and work.link.external
        sections in that order.

        Args:
            path: Path to install the product to (workarea root).
            dependencies: Whether to install dependencies.
            installer_path: Path where products are cloned (should contain products.lock.json).
                         If None, attempts to detect from path.

        """
        logger.info("Installing product %s to %s", self.name, path)
        ensure_directory(path)

        logger.info("Finding lock file in %s", path)
        lock_file, effective_installer_path = self._find_lock_file(path, installer_path)

        # Raise error if lock file is not found
        if not lock_file or not lock_file.exists():
            logger.error("Lock file not found at %s", lock_file)
            msg = f"products.lock.json not found. Expected at: {lock_file or 'unknown location'}"
            raise FileNotFoundError(msg)

        if not effective_installer_path:
            logger.error(
                "Installer path could not be determined from lock file location"
            )
            msg = "Installer path could not be determined from lock file location"
            raise ValueError(msg)

        products = self._load_products_from_lock(
            lock_file, effective_installer_path, dependencies=dependencies
        )

        logger.info("Loaded %d products from lock file", len(products))

        # If loading from lock failed, try to ensure installer is complete
        if not products and effective_installer_path:
            products = self._ensure_installer_complete(
                effective_installer_path, dependencies=dependencies
            )

        if not products:
            if dependencies:
                collection = self.get_dependencies(base_path=effective_installer_path)
                products = collection.products
            else:
                products = [self]

        logger.warning(
            "Products to process: %s", [product.dirname for product in products]
        )
        processed: set[Path] = set()

        for product in products:
            logger.warning("Processing product %s", product.name)
            if not product.dirname:
                logger.warning("Product %s has no dirname", product.name)
                continue

            self._process_product_work_config(product, path, processed)

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
        """Return string representation of ProductInstallable."""
        return f"ProductInstallable(name='{self.name}', version='{self.version}', type='{self.type}')"

    def __repr__(self) -> str:
        """Detailed string representation of ProductInstallable."""
        return (
            f"ProductInstallable(name='{self.name}', version='{self.version}', "
            f"type='{self.type}', parents={self.parents}, categories={self.categories})"
        )
