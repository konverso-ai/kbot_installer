"""ProductInstallable class for managing installable product definitions."""

# Pydantic model fields are validated at runtime; pylint infers FieldInfo on access.
# pylint: disable=no-member

import configparser
import contextlib
import fnmatch
import json
import os
import shutil
import site
import sys
from collections import deque
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import tomlkit
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from tomlkit.exceptions import TOMLKitError
from typing_extensions import Self, override

from git.provider import create_provider
from git.provider.base import ProviderBase
from installable.base import InstallableBase
from installable.factory import create_installable
from installable.product_collection import ProductCollection
from installer_support.installer_utils import ensure_directory, version_to_branch
from utils.Logger import logger
from utils.product import Product
from utils.version import Version

log = logger.get_package_logger("installable")

# Type alias for product configuration (INI-style: section -> option -> value)
ProductConfig = dict[str, dict[str, str]]

# Result type for get_kconf(): contains "aggregated" key and per-product configs
# Structure: {"aggregated": ProductConfig, product_name: ProductConfig, ...}
KbotConfigResult = dict[str, ProductConfig]


DEFAULT_PROVIDERS: list[str] = ["storage", "github", "bitbucket"]

_PRODUCT_FACTORY_KWARG_KEYS = frozenset(
    {
        "name",
        "version",
        "build",
        "date",
        "product_type",
        "type",
        "docs",
        "parents",
        "categories",
        "license_info",
        "license",
        "display",
        "build_details",
    }
)


class ProductInstallable(BaseModel, InstallableBase):
    """Orchestrates a Product and installable operations.

    Holds a :class:`~utils.product.Product` for metadata and implements
    :class:`InstallableBase` for installer workflows.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    product: Product
    env: Literal["dev", "prod"] = "dev"
    providers: Annotated[
        list[str], Field(default_factory=lambda: list(DEFAULT_PROVIDERS))
    ]
    dirname: Path | None = None
    provider_name_used: str | None = None
    branch_used: str | None = None
    branch: str | None = None
    _provider: ProviderBase = PrivateAttr()

    @model_validator(mode="before")
    @classmethod
    def _build_product_from_factory_kwargs(cls, data: object) -> object:
        """Nest a Product when flat factory keyword arguments are provided."""
        if not isinstance(data, dict) or "product" in data or "name" not in data:
            return data

        payload = dict(data)
        product_kwargs = {
            key: payload.pop(key)
            for key in list(payload)
            if key in _PRODUCT_FACTORY_KWARG_KEYS
        }
        payload["product"] = Product.from_dict(product_kwargs)
        return payload

    @override
    def model_post_init(self, context: Any, /) -> None:
        """Initialize the runtime git provider after model validation."""
        self._provider = create_provider(name="selector", providers=self.providers)

    @property
    def provider(self) -> ProviderBase:
        """Return the git provider used for clone operations."""
        return self._provider

    @provider.setter
    def provider(self, value: ProviderBase) -> None:
        """Replace the git provider (used in tests and provider overrides)."""
        self._provider = value

    def _load_product_by_name(
        self,
        product_name: str,
        base_path: Path | None = None,
        default_version: str | Version | None = None,
    ) -> Self:
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
        version = (
            default_version.to_str()
            if isinstance(default_version, Version)
            else (default_version or self.product.version.to_str())
        )
        # Use the same branch as the parent product if specified
        branch = self.branch

        # Try to load from cloned repository if base_path is provided
        if base_path:
            cloned_product_path = base_path / product_name
            if (cloned_product_path / "description.xml").exists():
                loaded = cast(
                    "Self",
                    create_installable(
                        "product",
                        name=product_name,
                        providers=providers,
                        version=version,
                        branch=branch,
                    ),
                )
                loaded.load_from_installer_folder(cloned_product_path)
                # If description.xml doesn't specify a version, keep the default version
                if not loaded.product.version and version:
                    loaded.product.version = Version.parse(version)
                return loaded

        # Otherwise, create a minimal product instance with just the name using factory
        # The provider will handle the actual loading when cloning
        # Pass providers, version, and branch to ensure dependencies use the same as the main product
        return cast(
            "Self",
            create_installable(
                "product",
                name=product_name,
                providers=providers,
                version=version,
                branch=branch,
            ),
        )

    @override
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

        xml_product = Product.from_xml_file(xml_path)
        if json_path.exists():
            json_data = json.loads(json_path.read_text(encoding="utf-8"))
            loaded_product = Product.merge(xml_product, Product.from_json(json_data))
            self.env = json_data.get("env", self.env)
        else:
            loaded_product = xml_product

        if not loaded_product.version and self.product.version:
            loaded_product = loaded_product.model_copy(
                update={"version": self.product.version}
            )

        self.product = loaded_product

    @classmethod
    def from_installer_folder(cls, folder_path: str | Path) -> Self | None:
        """Create a product installable from an installer folder.

        Args:
            folder_path: Path to the product folder containing ``description.xml``.

        Returns:
            Loaded product installable, or ``None`` when the folder is missing
            or invalid.

        """
        path = Path(folder_path)
        if not path.exists() or not (path / "description.xml").exists():
            return None

        try:
            product = create_installable("product", name=path.name)
            product.load_from_installer_folder(path)
        except (ValueError, FileNotFoundError):
            return None
        else:
            return cast("Self", product)

    @override
    def to_xml(self) -> str:
        """Convert Product to XML string.

        Returns:
            XML string representation.

        """
        return self.product.to_xml()

    @override
    def to_json(self) -> dict[str, Any]:
        """Convert product installable to a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the product and installable state.

        """
        data = self.product.to_json()
        data["env"] = self.env

        if self.product.build is not None:
            data["build"] = self.product.build_timestamp
            data["build_details"] = {
                "timestamp": self.product.build.timestamp,
                "branch": self.product.build.branch,
                "commit": self.product.build.commit,
            }
        else:
            data["build"] = None
            data["build_details"] = None

        if self.product.display is not None:
            data["display"] = self.product.display.model_dump(exclude_none=True)

        data["provider_name_used"] = self.provider_name_used
        data["branch_used"] = self.branch_used
        data["branch"] = self.branch
        return data

    @override
    def download(self, path: Path, *, dependencies: bool = True) -> None:
        """Download the product to the given path using breadth-first traversal.

        Args:
            path: Path to the directory that will contain the downloaded products.
            dependencies: Whether to download dependencies.

        """
        # Ensure the base path exists
        path.mkdir(parents=True, exist_ok=True)

        # Use specified branch if provided, otherwise convert version to branch name
        # Store the calculated branch in self.branch so it's preserved and can be used by dependencies
        if not self.branch and self.product.version:
            self.branch = version_to_branch(self.product.version.to_str(), env=self.env)
        branch = self.branch

        if not dependencies:
            log.warning(
                "Downloading %s (branch: %s) to %s",
                self.product.name,
                branch,
                path,
            )
            product_path = path / self.product.name
            self.provider.clone_and_checkout(
                product_path, branch, repository_name=self.product.name
            )
            # Store the provider and branch used (providers update these during clone)
            self.provider_name_used = self.provider.get_name()
            self.branch_used = self.provider.get_branch()
            # Only load if description.xml exists (clone may have failed)
            if (product_path / "description.xml").exists():
                self.load_from_installer_folder(product_path)
            return

        # First, clone the main product to get its dependencies
        main_product_path = path / self.product.name
        self.provider.clone_and_checkout(
            main_product_path, branch, repository_name=self.product.name
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
            if current_product.product.name in processed:
                continue

            # Clone current product if not already cloned (main product is already cloned)
            if (
                current_product.product.name != self.product.name
                and not self._download_dependency_product(
                    current_product, path, processed
                )
            ):
                continue

            # Mark as processed
            processed.add(current_product.product.name)

            # Discover new dependencies from the (now loaded) current product
            self._discover_and_queue_parents(current_product, queue, processed, path)

    def _download_dependency_product(
        self, product: Self, base_path: Path, processed: set[str]
    ) -> bool:
        """Download a dependency product.

        Args:
            product: Product to download.
            base_path: Base path for downloading.
            processed: Set of processed product names.

        Returns:
            True if download was successful, False otherwise.

        """
        # Use specified branch if provided, otherwise convert version to branch name
        # Store the calculated branch in product.branch so it's preserved
        if not product.branch and product.product.version:
            product.branch = version_to_branch(
                product.product.version.to_str(), env=product.env
            )
        dependency_branch = product.branch
        product_path = base_path / product.product.name

        try:
            # Clone with branch fallback handled by selector_provider using config.branches
            product.provider.clone_and_checkout(
                product_path,
                dependency_branch,
                repository_name=product.product.name,
            )
            # Store the provider and branch used (providers update these during clone)
            product.provider_name_used = product.provider.get_name()
            product.branch_used = product.provider.get_branch()
        except Exception:
            # Clone failed - selector_provider already tried all fallback branches from config
            log.exception("Failed to download %s", product.product.name)
            # Mark as processed even if clone failed to avoid infinite loop
            processed.add(product.product.name)
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
        current_product: Self,
        queue: deque[Self],
        processed: set[str],
        base_path: Path,
    ) -> None:
        """Discover and queue parent products for downloading.

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
        if current_product.product.name == self.product.name:
            # Main product: should have been loaded already
            should_process_parents = True
        elif (
            current_product.dirname
            and (current_product.dirname / "description.xml").exists()
        ):
            # Cloned product: verify it was successfully loaded
            should_process_parents = True

        if should_process_parents:
            for parent_name in current_product.product.parent_names:
                if parent_name not in processed:
                    # Load parent product - try from cloned repo first, otherwise create minimal instance
                    parent_product = self._load_product_by_name(
                        parent_name,
                        base_path=base_path,
                        default_version=current_product.product.version,
                    )
                    queue.append(parent_product)

    @override
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

            if current_product.product.name in processed:
                continue

            collected_products.append(current_product)
            processed.add(current_product.product.name)

            # Add dependencies to queue
            # Pass current product's version as default so dependencies inherit it
            for parent_name in current_product.product.parent_names:
                if parent_name not in processed:
                    parent_product = self._load_product_by_name(
                        parent_name,
                        base_path=base_path,
                        default_version=current_product.product.version,
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
            msg = f"Product {self.product.name} has no dirname set"
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
                result[prod.product.name] = {}
                continue

            # Parse INI-style config file
            parser = configparser.ConfigParser()
            try:
                parser.read(conf_path, encoding="utf-8")
            except configparser.Error:
                result[prod.product.name] = {}
                continue

            # Convert to dict
            prod_config: ProductConfig = {}
            for section in parser.sections():
                prod_config[section] = dict(parser[section])

            result[prod.product.name] = prod_config

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

    def _resolve_installer_path(
        self, workarea_path: Path, installer_path: Path | None
    ) -> Path:
        """Resolve the installer directory for workarea installation.

        Args:
            workarea_path: Workarea destination path.
            installer_path: Explicit installer directory when provided.

        Returns:
            Resolved installer directory path.

        Raises:
            ValueError: If the installer path cannot be determined.

        """
        if installer_path is not None:
            return installer_path.resolve()

        msg = (
            f"installer_path is required to install products into {workarea_path}. "
            "Pass the directory where products were cloned."
        )
        raise ValueError(msg)

    def _load_products_for_install(
        self, installer_path: Path, *, dependencies: bool
    ) -> list[Self]:
        """Load products from the installer directory for workarea installation.

        Args:
            installer_path: Path to the installer directory.
            dependencies: Whether to include dependency products.

        Returns:
            Products to process, loaded from cloned repositories when available.

        """
        if not dependencies:
            product_dir = installer_path / self.product.name
            loaded = ProductInstallable.from_installer_folder(product_dir)
            return [cast("Self", loaded)] if loaded else []

        root_dir = installer_path / self.product.name
        if root_dir.exists() and (root_dir / "description.xml").exists():
            self.load_from_installer_folder(root_dir)

        return cast(
            "list[Self]",
            self.get_dependencies(base_path=installer_path).products,
        )

    def _process_product_work_config(
        self,
        product: Self,
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
            log.warning("Product %s has no pyproject.toml", product.product.name)
            return

        try:
            with pyproject_file.open(encoding="utf-8") as f:
                pyproject_data = tomlkit.load(f)
        except (OSError, TOMLKitError):
            log.warning(
                "Failed to load pyproject.toml for product %s", product.product.name
            )
            return

        work_raw = pyproject_data.get("work")
        if not work_raw:
            return

        work_config = work_raw.unwrap()
        init_config = work_config.get("init", {})
        copy_config = work_config.get("copy", {})
        ignore_config = work_config.get("ignore", {})
        link_config = work_config.get("link", {})
        link_section = work_config.get("link", {})
        link_external_config = link_section.get("external", {})

        if init_config:
            log.warning("Processing init section for product %s", product.product.name)
            self._handle_work_init(workarea_root, init_config, processed)

        if copy_config and product.dirname is not None:
            log.warning("Processing copy section for product %s", product.product.name)
            self._handle_work_copy(
                workarea_root, product.dirname, copy_config, ignore_config, processed
            )

        if link_config and product.dirname is not None:
            log.warning("Processing link section for product %s", product.product.name)
            self._handle_work_link(
                workarea_root, product.dirname, link_config, ignore_config, processed
            )

        if link_external_config:
            log.warning(
                "Processing link.external section for product %s",
                product.product.name,
            )
            self._handle_work_link_external(
                workarea_root, link_external_config, processed
            )

    @override
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
            installer_path: Path where products are cloned. Required.

        """
        log.debug("Installing product %s to %s", self.product.name, path)
        ensure_directory(path)

        effective_installer_path = self._resolve_installer_path(path, installer_path)
        products = self._load_products_for_install(
            effective_installer_path, dependencies=dependencies
        )

        log.debug("Loaded %d products from installer directory", len(products))

        if not products:
            log.debug(
                "Installer incomplete at %s, downloading products",
                effective_installer_path,
            )
            self.download(effective_installer_path, dependencies=dependencies)
            products = self._load_products_for_install(
                effective_installer_path, dependencies=dependencies
            )

        if not products:
            msg = (
                f"No products found in installer directory: {effective_installer_path}"
            )
            raise FileNotFoundError(msg)

        log.warning(
            "Products to process: %s", [product.dirname for product in products]
        )
        processed: set[Path] = set()

        for product in products:
            log.warning("Processing product %s", product.product.name)
            if not product.dirname:
                log.warning("Product %s has no dirname", product.product.name)
                continue

            self._process_product_work_config(product, path, processed)

    @override
    def update(self, path: Path, *, dependencies: bool = True) -> None:
        """Update the product in the workarea.

        Args:
            path: Path to update the product from.
            dependencies: Whether to update dependencies.

        """
        msg = "Update is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def uninstall(self, path: Path) -> None:
        """Uninstall the product from the workarea.

        Args:
            path: Path to uninstall the product from.

        """
        msg = "Uninstall is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def repair(self, path: Path, *, dependencies: bool = True) -> None:
        """Repair the product in the workarea.

        Args:
            path: Path to repair the product from.
            dependencies: Whether to repair dependencies.

        """
        msg = "Repair is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def upgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Upgrade the product in the workarea.

        Args:
            path: Path to upgrade the product from.
            dependencies: Whether to upgrade dependencies.

        """
        msg = "Upgrade is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def downgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Downgrade the product in the workarea.

        Args:
            path: Path to downgrade the product from.
            dependencies: Whether to downgrade dependencies.

        """
        msg = "Downgrade is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def backup(self, path: Path) -> None:
        """Backup the product in the given path.

        Args:
            path: Path to backup the product from.

        """
        msg = "Backup is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def restore(self, path: Path) -> None:
        """Restore the product in the given path.

        Args:
            path: Path to restore the product from.

        """
        msg = "Restore is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def delete(self, path: Path) -> None:
        """Delete the product in the given path.

        Args:
            path: Path to delete the product from.

        """
        msg = "Delete is not implemented yet"
        raise NotImplementedError(msg) from None

    @override
    def __str__(self) -> str:
        """Return string representation of ProductInstallable."""
        return (
            f"ProductInstallable(name='{self.product.name}', "
            f"version='{self.product.version.to_str()}', type='{self.product.type}')"
        )

    @override
    def __repr__(self) -> str:
        """Detailed string representation of ProductInstallable."""
        return (
            f"ProductInstallable(name='{self.product.name}', "
            f"version='{self.product.version.to_str()}', type='{self.product.type}', "
            f"parents={self.product.parent_names}, "
            f"categories={self.product.category_names})"
        )


ProductCollection.model_rebuild()
