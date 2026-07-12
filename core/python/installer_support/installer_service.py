"""InstallerService for managing product installation."""

import shutil
import subprocess
from pathlib import Path
from typing import cast

from git.provider import (
    DEFAULT_PROVIDERS_CONFIG,
    create_provider,
)
from git.provider.base import ProviderBase
from git.provider.config import ProvidersConfig
from git.provider.credential_manager import CredentialManager
from git.provider.storage_provider import StorageProvider
from installable.dependency_graph import DependencyGraph
from installable.factory import create_installable
from installable.product_collection import ProductCollection
from installable.product_installable import ProductInstallable
from installable.renderer import DependencyTreeRenderer
from installer_support.installation_table import InstallationTable
from installer_support.installer_utils import ensure_directory, version_to_branch
from storage.base import StorageBackend, StorageBase
from utils.Logger import logger

log = logger.getPackageLogger("installer_support")


def _providers_config_with_storage_backend(
    storage_backend: StorageBackend | None,
) -> ProvidersConfig:
    """Return provider configuration with an optional storage backend override."""
    if storage_backend is None:
        return DEFAULT_PROVIDERS_CONFIG

    return DEFAULT_PROVIDERS_CONFIG.model_copy(
        update={
            "storage": DEFAULT_PROVIDERS_CONFIG.storage.model_copy(
                update={"backend": storage_backend.value}
            )
        }
    )


class InstallerService:
    """Service for installing kbot products and managing dependencies.

    This service provides methods that correspond directly to CLI commands:
    - install(): Install a product and optionally its dependencies
    - list(): List installed products (as list or tree)
    - repair(): Repair/update products in the installer

    Attributes:
        installer_dir: Path to the installer directory.
        providers: List of provider names to try in order.

    """

    def __init__(
        self,
        installer_dir: str | Path,
        providers: list[str] | None = None,
        storage_backend: StorageBackend | None = None,
        *,
        verbose: bool = False,
    ) -> None:
        """Initialize the installer service.

        Args:
            installer_dir: Path to the installer directory.
            providers: List of provider names to try. Defaults to ["storage", "github", "bitbucket"].
            storage_backend: Storage backend override for the storage provider.
                Defaults to the value from the providers configuration file.
            verbose: When True, show skipped products and detailed provider output.

        """
        self.installer_dir = Path(installer_dir)
        self.providers = providers or ["storage", "github", "bitbucket"]
        self.verbose = verbose
        self._providers_config = _providers_config_with_storage_backend(storage_backend)
        self._storage: StorageBase | None = None

        # Initialize services
        self.selector_provider: ProviderBase = create_provider(
            name="selector",
            providers=self.providers,
            config=self._providers_config,
            quiet=not verbose,
        )
        self.installation_table = InstallationTable(verbose=verbose)

    def download(
        self,
        product_name: str,
        version: str,
        *,
        include_dependencies: bool = True,
    ) -> None:
        """Install a product and optionally its dependencies.

        This method corresponds to the 'download' CLI command.
        - Downloads the specified product
        - If include_dependencies=True, downloads all parent dependencies
        - If include_dependencies=False, downloads only the specified product
        - Skips products that are already downloaded

        Args:
            product_name: Name of the product to install.
            version: Version of the product.
            include_dependencies: Whether to install dependencies.

        Raises:
            ValueError: If installation fails.

        """
        log.info(
            "Installing product '%s' version '%s' (dependencies: %s)",
            product_name,
            version,
            include_dependencies,
        )

        # Ensure installer directory exists
        ensure_directory(self.installer_dir)

        # Load product definitions from repository (this will download the main product)
        log.info("Loading product definitions...")
        self._load_product_from_repository(product_name, version)

        # Install dependencies if requested
        if include_dependencies:
            log.info("Installing dependencies...")
            self._install_dependencies_recursively(product_name, version)

        log.info("Installation completed for product '%s'", product_name)

    def download_bundle(
        self,
        bundle_name: str,
        bundle_version: str,
        top_product: str,
        *,
        include_dependencies: bool = True,
    ) -> None:
        """Download products from a bundle descriptor stored in object storage.

        This method corresponds to the bundle mode of the ``download`` CLI command.

        Args:
            bundle_name: Name of the bundle.
            bundle_version: Version of the bundle.
            top_product: Root product defining the highest installation level.
            include_dependencies: Whether to download parent dependencies.

        Raises:
            ValueError: If the bundle or top product cannot be resolved.

        """
        installable = create_installable(
            "bundle",
            bundle_name=bundle_name,
            bundle_version=bundle_version,
            top_product=top_product,
            installer_dir=self.installer_dir,
            storage=self._get_storage(),
            installation_table=self.installation_table,
            storage_backend=self._providers_config.storage.backend,
            verbose=self.verbose,
        )
        installable.download(dependencies=include_dependencies)

    def list_products(self, *, as_tree: bool = False, verbose: bool = False) -> str:
        """List installed products.

        This method corresponds to the 'list' CLI command.
        - Lists products that are currently installed in the installer directory
        - Shows as simple list or dependency tree
        - Does not download anything

        Args:
            as_tree: Whether to show as dependency tree.
            verbose: Show all subtrees even if already displayed.

        Returns:
            Formatted string listing products.

        """
        log.info("Listing installed products (tree: %s)", as_tree)

        # Load products from installer directory
        product_collection = self._load_products_from_installer_directory()

        if not product_collection:
            return "No products installed."

        products = product_collection.get_all_products()
        if not products:
            return "No products installed."

        if as_tree:
            # Create dependency graph and render as tree
            dependency_graph = DependencyGraph(products)
            renderer = DependencyTreeRenderer()
            return renderer.render_uv_tree_style(dependency_graph, verbose=verbose)

        # Simple list format
        lines = ["Installed products:", "=================="]
        for product in products:
            lines.append(f"- {product.product.name} ({product.product.type})")
            if product.product.parent_names:
                lines.append(
                    f"  Dependencies: {', '.join(product.product.parent_names)}"
                )
        return "\n".join(lines)

    def repair(
        self,
        product_name: str,
        version: str | None = None,
    ) -> list[str]:
        """Repair a product by correcting/adding/updating products.

        This method corresponds to the 'repair' CLI command.
        - Detects missing or incorrect products
        - Adds missing products
        - Updates products to correct version
        - Fixes corrupted installations

        Args:
            product_name: Name of the product to repair.
            version: Version of the product. If None, will try to detect from existing installation.

        Returns:
            List of repaired product names.

        Raises:
            ValueError: If repair fails.

        """
        log.info("Repairing product '%s' (version: %s)", product_name, version)

        # Load existing products to understand current state
        existing_products = self._load_products_from_installer_directory()

        # Load product definitions from repository to get target state
        self._load_product_from_repository(product_name, version or "master")

        # Install dependencies recursively to get all required products
        self._install_dependencies_recursively(product_name, version or "master")

        # Get target products (what should be installed)
        target_products = self._get_products_with_dependencies(product_name)
        target_product_names = {p.product.name for p in target_products}

        # Repair products that need fixing
        repaired_products = self._repair_products(target_products, version)

        # Remove extra products that shouldn't be there
        self._remove_extra_products(existing_products, target_product_names)

        log.info("Repair completed. Repaired products: %s", repaired_products)
        return repaired_products

    def _repair_products(
        self, target_products: list[ProductInstallable], version: str | None
    ) -> list[str]:
        """Repair products that need fixing."""
        repaired_products = []

        for product in target_products:
            product_dir = self.installer_dir / product.product.name
            needs_repair, repair_reason = self._check_product_needs_repair(
                product_dir, product.product.name, version
            )

            if needs_repair:
                log.info(
                    "Repairing product '%s' (%s)", product.product.name, repair_reason
                )
                self._repair_single_product(product_dir, product, version or "master")
                repaired_products.append(product.product.name)

        return repaired_products

    def _check_product_needs_repair(
        self, product_dir: Path, product_name: str, version: str | None
    ) -> tuple[bool, str]:
        """Check if a product needs repair and return reason."""
        if not product_dir.exists():
            return True, "missing"
        if not any(product_dir.iterdir()):
            return True, "empty"
        if version and not self._is_product_at_version(product_name, version):
            return True, "wrong version"
        return False, ""

    def _repair_single_product(
        self, product_dir: Path, product: ProductInstallable, version: str
    ) -> None:
        """Repair a single product by removing and reinstalling."""
        # Remove existing directory if it exists
        if product_dir.exists():
            shutil.rmtree(product_dir)

        # Reinstall the product
        self._install_single_product(product, version)

    def _remove_extra_products(
        self,
        existing_products: ProductCollection | None,
        target_product_names: set[str],
    ) -> None:
        """Remove products that shouldn't be there."""
        if not existing_products:
            return

        existing_product_names = {
            p.product.name for p in existing_products.get_all_products()
        }
        extra_products = existing_product_names - target_product_names

        for extra_product in extra_products:
            if extra_product != "kbot_installer":  # Don't remove installer itself
                log.info("Removing extra product: %s", extra_product)
                extra_dir = self.installer_dir / extra_product
                if extra_dir.exists():
                    shutil.rmtree(extra_dir)

    def get_installation_table(self) -> InstallationTable:
        """Get the installation results table.

        Returns:
            InstallationTable containing all installation results.

        """
        return self.installation_table

    # Private helper methods

    def _get_storage(self) -> StorageBase:
        """Return the configured object storage backend."""
        if self._storage is None:
            credential_manager = CredentialManager(self._providers_config)
            auth = credential_manager.get_auth_for_provider("storage")
            provider = create_provider(
                "storage",
                config=self._providers_config,
                auth=auth,
                quiet=not self.verbose,
            )
            self._storage = cast("StorageProvider", provider)._storage
        return self._storage

    def _load_product_from_repository(self, product_name: str, version: str) -> None:
        """Load a single product from repository."""
        log.debug(
            "Loading product '%s' from repository (version: %s)", product_name, version
        )

        # Create product directory
        product_dir = self.installer_dir / product_name
        product_dir.mkdir(parents=True, exist_ok=True)

        # Get branch for the version
        branch = version_to_branch(version)

        # Clone repository
        log.debug(
            "Cloning repository for product: %s (branch: %s)", product_name, branch
        )
        self.installation_table.begin_installation(product_name)
        self.selector_provider.clone_and_checkout(
            product_dir, branch, repository_name=product_name
        )

        # Use the actual provider name that was used for cloning (not "selector")
        actual_provider_name = self.selector_provider.get_name()
        self.installation_table.complete_installation(
            product_name=product_name,
            provider_name=actual_provider_name,
            status="success",
        )

    def _install_dependencies_recursively(
        self, product_name: str, version: str
    ) -> None:
        """Install all dependencies for a product recursively."""
        log.debug(
            "Installing dependencies for product '%s' (version: %s)",
            product_name,
            version,
        )

        # Load the main product to get its dependencies
        main_product = self._get_product(product_name)
        if not main_product or not main_product.product.parent_names:
            log.debug("No dependencies to install for product '%s'", product_name)
            return

        # Install each dependency
        for dep_name in main_product.product.parent_names:
            if dep_name != "kbot_installer":  # Skip self-installation
                log.debug("Installing dependency: %s", dep_name)
                try:
                    if self._is_product_installed(dep_name):
                        log.info(
                            "Product '%s' already installed, skipping", dep_name
                        )
                        # Detect the provider that was used for this cached product
                        cached_provider = self._detect_cached_provider(dep_name)
                        self.installation_table.complete_installation(
                            product_name=dep_name,
                            provider_name=f"{cached_provider} (cached)",
                            status="skipped",
                        )
                    else:
                        log.info("Installing product: %s", dep_name)
                        self._load_product_from_repository(dep_name, version)

                    # Recursively install dependencies of this dependency
                    self._install_dependencies_recursively(dep_name, version)
                except Exception as e:
                    log.warning("Failed to install dependency '%s': %s", dep_name, e)
                    # Continue with other dependencies
                    continue

    def _get_product(self, product_name: str) -> ProductInstallable:
        """Get a product by name from the installer directory."""
        product_dir = self.installer_dir / product_name
        product = ProductInstallable.from_installer_folder(product_dir)
        if not product:
            error_msg = f"Product '{product_name}' not found"
            raise ValueError(error_msg)
        return product

    def _get_products_with_dependencies(
        self, product_name: str
    ) -> list[ProductInstallable]:
        """Get a product and all its dependencies."""
        # Load all products from installer directory
        product_collection = self._load_products_from_installer_directory()
        if not product_collection:
            # If no products loaded, just return the main product
            return [self._get_product(product_name)]

        # Create dependency graph
        dependency_graph = DependencyGraph(product_collection.get_all_products())

        # Get all dependencies
        all_dependencies = dependency_graph.get_transitive_dependencies(product_name)

        # Build list of products
        products = [self._get_product(product_name)]
        for dep_name in all_dependencies:
            if dep_name != product_name:  # Avoid duplicates
                try:
                    products.append(self._get_product(dep_name))
                except (ValueError, Exception) as e:
                    log.warning(
                        "Dependency '%s' not found or invalid: %s", dep_name, e
                    )
                    continue

        return products

    def _load_products_from_installer_directory(self) -> ProductCollection | None:
        """Load products from the installer directory."""
        log.debug(
            "Loading products from installer directory: %s", self.installer_dir
        )

        try:
            product_collection = ProductCollection.from_installer(
                str(self.installer_dir)
            )
            if product_collection:
                products = product_collection.get_all_products()
                log.debug(
                    "Loaded %d products from installer directory", len(products)
                )
            else:
                return None
        except Exception as e:
            log.debug("Failed to load products from installer directory: %s", e)
            return None
        return product_collection

    def _is_product_installed(self, product_name: str) -> bool:
        """Check if a product is already installed."""
        product_dir = self.installer_dir / product_name
        return product_dir.exists() and any(product_dir.iterdir())

    def _is_product_at_version(self, product_name: str, version: str) -> bool:
        """Check if a product is at the specified version.

        Args:
            product_name: Name of the product to check.
            version: Version to check against.

        Returns:
            bool: True if product is at the specified version, False otherwise.

        """
        try:
            product_dir = self.installer_dir / product_name
            if not product_dir.exists():
                return False

            # Security: Safe subprocess usage - command executable resolved via shutil.which(),
            # command arguments are hardcoded, no user input passed as command arguments.
            # Only cwd (directory path) comes from product_name, which is validated (exists() check)
            # and comes from trusted installer directory structure. No command injection risk.
            git_path = shutil.which("git")
            if not git_path:
                log.debug("git command not found in PATH")
                return False

            result = subprocess.run(  # noqa: S603 - git_path resolved via shutil.which(), args hardcoded, cwd validated
                [git_path, "branch", "--show-current"],
                check=False,
                cwd=product_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                current_branch = result.stdout.strip()
                expected_branch = version_to_branch(version)
                return current_branch == expected_branch
        except Exception as e:
            error_msg = f"Failed to check version for product {product_name}: {e}"
            log.debug(error_msg)

        return False

    def _detect_cached_provider(self, product_name: str) -> str:
        """Detect which provider was used to install a cached product.

        This method tries to determine the provider by examining the product directory
        and checking for provider-specific characteristics.

        Args:
            product_name: Name of the product to check.

        Returns:
            Name of the detected provider or "unknown" if detection fails.

        """
        try:
            product_dir = self.installer_dir / product_name
            if not product_dir.exists():
                return "unknown"

            # Check for git repository first
            provider = self._detect_git_provider(product_dir)
            if provider != "unknown":
                return provider

            # Check for Nexus-specific indicators
            provider = self._detect_nexus_provider(product_dir)
            if provider != "unknown":
                return provider
            # Default fallback

        except Exception as e:
            log.debug(
                "Failed to detect provider for product %s: %s", product_name, e
            )
            return "unknown"

        return "unknown"

    def _detect_git_provider(self, product_dir: Path) -> str:
        """Detect git-based providers (GitHub, Bitbucket, Git)."""
        git_dir = product_dir / ".git"
        if not git_dir.exists():
            return "unknown"

        # Try to get remote URL to determine provider
        # Security: Safe subprocess usage - command executable resolved via shutil.which(),
        # command arguments are hardcoded, no user input passed as command arguments.
        # Only cwd (directory path) is validated (git_dir.exists() check) and comes from
        # trusted installer directory structure. No command injection risk.
        git_path = shutil.which("git")
        if not git_path:
            return "unknown"

        result = subprocess.run(  # noqa: S603 - git_path resolved via shutil.which(), args hardcoded, cwd validated
            [git_path, "remote", "get-url", "origin"],
            check=False,
            cwd=product_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            remote_url = result.stdout.strip()
            if "github.com" in remote_url:
                return "github"
            if "bitbucket.org" in remote_url:
                return "bitbucket"
            return "git"

        return "unknown"

    def _detect_nexus_provider(self, product_dir: Path) -> str:
        """Detect Nexus provider based on file indicators."""
        # Check for archive files
        if any(product_dir.glob("*.tar.gz")) or any(product_dir.glob("*.zip")):
            return "storage"

        # Check for common product files that indicate storage installation
        storage_indicators = [
            "description.json",
            "description.xml",
            "requirements.txt",
        ]
        if any((product_dir / indicator).exists() for indicator in storage_indicators):
            return "storage"

        return "unknown"

    def _install_single_product(
        self, product: ProductInstallable, version: str
    ) -> None:
        """Install a single product."""
        log.debug(
            "Installing single product: %s (version: %s)",
            product.product.name,
            version,
        )

        # Skip self-installation
        if product.product.name == "kbot_installer":
            log.info("Skipping self-installation of kbot_installer")
            self.installation_table.complete_installation(
                product_name=product.product.name,
                provider_name="self",
                status="skipped",
            )
            return

        # Get branch for the version
        branch = version_to_branch(version)

        # Create product directory
        product_dir = self.installer_dir / product.product.name

        # Remove existing directory to ensure fresh installation
        if product_dir.exists():
            shutil.rmtree(product_dir)
            log.debug(
                "Removed existing directory for product: %s", product.product.name
            )

        # Ensure directory exists
        ensure_directory(product_dir)

        # Clone repository
        log.debug(
            "Cloning %s (branch: %s) to %s",
            product.product.name,
            branch,
            product_dir,
        )
        self.installation_table.begin_installation(product.product.name)
        self.selector_provider.clone_and_checkout(
            product_dir, branch, repository_name=product.product.name
        )

        actual_provider_name = self.selector_provider.get_name()
        self.installation_table.complete_installation(
            product_name=product.product.name,
            provider_name=actual_provider_name,
            status="success",
        )

        log.info("Successfully installed product: %s", product.product.name)
