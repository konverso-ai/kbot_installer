"""WorkareaInstallable class for managing workarea installations."""

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from kbot_installer.core.installable.installable_base import InstallableBase
from kbot_installer.core.installable.product_collection import ProductCollection
from kbot_installer.core.interactivity.base import InteractivePrompter
from kbot_installer.core.setup.database_setup import (
    ExternalDatabaseSetupManager,
    InternalDatabaseSetupManager,
)
from kbot_installer.core.utils import ensure_directory

logger = logging.getLogger(__name__)


@dataclass
class WorkareaInstallable(InstallableBase):
    """Represents a workarea with its products and database configuration.

    Attributes:
        name: Workarea name (typically derived from path).
        target: Path to the workarea directory.
        installer_path: Path to installer directory (contains products.lock.json).
        db_internal: Whether to use internal PostgreSQL database.
        db_host: Database hostname (for external database).
        db_port: Database port number.
        db_name: Database name.
        db_user: Database user name.
        db_password: Database password.
        products: Product collection loaded from installer.
        prompter: Optional InteractivePrompter for user interaction.
        silent_mode: Suppress interactive prompts.

    """

    name: str = "workarea"
    target: Path = field(default_factory=lambda: Path.cwd())
    installer_path: Path | None = None
    db_internal: bool = True
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: str = "kbot_db"
    db_user: str = "kbot_db_user"
    db_password: str = "kbot_db_pwd"  # noqa: S105  # Default password
    products: ProductCollection = field(default_factory=ProductCollection)
    prompter: InteractivePrompter | None = None
    silent_mode: bool = False

    def load_from_installer_folder(self, folder_path: Path) -> None:
        """Load workarea data from installer folder.

        Args:
            folder_path: Path to installer directory (should contain products.lock.json).

        Raises:
            FileNotFoundError: If products.lock.json doesn't exist.
            ValueError: If JSON is invalid.

        """
        lock_file = folder_path / "products.lock.json"
        if not lock_file.exists():
            msg = f"products.lock.json not found in {folder_path}"
            raise FileNotFoundError(msg)

        self.installer_path = folder_path.resolve()
        self.products = ProductCollection.from_json(str(lock_file))

    def to_xml(self) -> str:
        """Convert Workarea to XML string.

        Returns:
            XML string representation.

        """
        root = ET.Element("workarea")
        root.set("name", self.name)
        root.set("target", str(self.target))
        if self.installer_path:
            root.set("installer_path", str(self.installer_path))

        db_elem = ET.SubElement(root, "database")
        db_elem.set("internal", str(self.db_internal).lower())
        db_elem.set("host", self.db_host)
        db_elem.set("port", self.db_port)
        db_elem.set("name", self.db_name)
        db_elem.set("user", self.db_user)

        products_elem = ET.SubElement(root, "products")
        products_elem.set("count", str(len(self.products.products)))

        return ET.tostring(root, encoding="unicode")

    def to_json(self) -> str:
        """Convert Workarea to JSON string.

        Returns:
            JSON string representation.

        """
        data = {
            "name": self.name,
            "target": str(self.target),
            "installer_path": str(self.installer_path) if self.installer_path else None,
            "database": {
                "internal": self.db_internal,
                "host": self.db_host,
                "port": self.db_port,
                "name": self.db_name,
                "user": self.db_user,
                # Note: password is not included in JSON for security
            },
            "products_count": len(self.products.products),
        }
        return json.dumps(data, indent=2)

    def clone(self, path: Path, *, dependencies: bool = True) -> None:
        """Clone is not applicable for workarea.

        Args:
            path: Path to clone to (not used).
            dependencies: Whether to clone dependencies (not used).

        Raises:
            NotImplementedError: Always raised as clone is not applicable for workarea.

        """
        msg = "Clone is not applicable for workarea. Use install() instead."
        raise NotImplementedError(msg)

    def get_dependencies(self) -> ProductCollection:
        """Get ProductCollection containing all products in workarea.

        Returns:
            ProductCollection with all products.

        """
        return self.products

    def install(self, path: Path, *, _dependencies: bool = True) -> None:
        """Install the workarea and set up database.

        Args:
            path: Path to install workarea to (same as target if not specified).
            dependencies: Whether to install dependencies (ignored, all products are used).

        """
        self.target = path.resolve()
        ensure_directory(self.target)

        # Ensure that logs directory exists
        logs_dir = self.target / "logs"
        ensure_directory(logs_dir)

        # Ensure we have products loaded
        if not self.products.products and self.installer_path:
            lock_file = self.installer_path / "products.lock.json"
            if lock_file.exists():
                self.products = ProductCollection.from_json(str(lock_file))
            else:
                logger.warning(
                    "No products.lock.json found in %s. Database setup will proceed without products.",
                    self.installer_path,
                )

        # Set up database using appropriate manager
        if self.db_internal:
            db_manager = InternalDatabaseSetupManager(
                target=self.target,
                products=self.products.products,
                prompter=self.prompter,
                db_port=self.db_port,
                db_name=self.db_name,
                db_user=self.db_user,
                db_password=self.db_password,
                silent_mode=self.silent_mode,
            )
        else:
            db_manager = ExternalDatabaseSetupManager(
                target=self.target,
                products=self.products.products,
                prompter=self.prompter,
                db_host=self.db_host,
                db_port=self.db_port,
                db_name=self.db_name,
                db_user=self.db_user,
                db_password=self.db_password,
                silent_mode=self.silent_mode,
            )

        logger.info("Setting up database for workarea at %s", self.target)
        db_manager.setup()

    def setup_database_only(self, path: Path) -> None:
        """Set up database only (without loading schema).

        Args:
            path: Path to install workarea to.

        """
        self.target = path.resolve()
        ensure_directory(self.target)

        # Ensure that logs directory exists
        logs_dir = self.target / "logs"
        ensure_directory(logs_dir)

        # Set up database using appropriate manager (without schema)
        if self.db_internal:
            db_manager = InternalDatabaseSetupManager(
                target=self.target,
                products=[],  # No products at init stage
                prompter=self.prompter,
                db_port=self.db_port,
                db_name=self.db_name,
                db_user=self.db_user,
                db_password=self.db_password,
                silent_mode=self.silent_mode,
            )
            db_manager.setup_database_only()
        else:
            db_manager = ExternalDatabaseSetupManager(
                target=self.target,
                products=[],  # No products at init stage
                prompter=self.prompter,
                db_host=self.db_host,
                db_port=self.db_port,
                db_name=self.db_name,
                db_user=self.db_user,
                db_password=self.db_password,
                silent_mode=self.silent_mode,
            )
            db_manager.setup_database_only()

        logger.info(
            "Database initialized (without schema) for workarea at %s", self.target
        )

    def update(self, path: Path, *, dependencies: bool = True) -> None:
        """Update the workarea.

        Args:
            path: Path to update workarea at.
            dependencies: Whether to update dependencies.

        """
        msg = "Update is not implemented yet"
        raise NotImplementedError(msg)

    def uninstall(self, path: Path) -> None:
        """Uninstall the workarea.

        Args:
            path: Path to uninstall workarea from.

        """
        msg = "Uninstall is not implemented yet"
        raise NotImplementedError(msg)

    def repair(self, path: Path, *, dependencies: bool = True) -> None:
        """Repair the workarea.

        Args:
            path: Path to repair workarea at.
            dependencies: Whether to repair dependencies.

        """
        msg = "Repair is not implemented yet"
        raise NotImplementedError(msg)

    def upgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Upgrade the workarea.

        Args:
            path: Path to upgrade workarea at.
            dependencies: Whether to upgrade dependencies.

        """
        msg = "Upgrade is not implemented yet"
        raise NotImplementedError(msg)

    def downgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Downgrade the workarea.

        Args:
            path: Path to downgrade workarea at.
            dependencies: Whether to downgrade dependencies.

        """
        msg = "Downgrade is not implemented yet"
        raise NotImplementedError(msg)

    def backup(self, path: Path) -> None:
        """Backup the workarea.

        Args:
            path: Path to backup workarea from.

        """
        msg = "Backup is not implemented yet"
        raise NotImplementedError(msg)

    def restore(self, path: Path) -> None:
        """Restore the workarea.

        Args:
            path: Path to restore workarea from.

        """
        msg = "Restore is not implemented yet"
        raise NotImplementedError(msg)

    def delete(self, path: Path) -> None:
        """Delete the workarea.

        Args:
            path: Path to delete workarea from.

        """
        msg = "Delete is not implemented yet"
        raise NotImplementedError(msg)
