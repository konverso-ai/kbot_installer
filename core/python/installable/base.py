"""Base interface for installable products."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from installable.product_collection import ProductCollection


class InstallableBase(ABC):
    """Base interface for installable products.

    This interface defines the contract that all installable products must implement.
    """

    @abstractmethod
    def load_from_installer_folder(self, folder_path: Path) -> None:
        """Load product data from installer folder (XML + optional JSON) into current instance.

        Args:
            folder_path: Path to product folder.

        Raises:
            FileNotFoundError: If description.xml doesn't exist.
            ValueError: If XML is invalid.

        """

    @abstractmethod
    def to_xml(self) -> str:
        """Convert Product to XML string.

        Returns:
            XML string representation.

        """

    @abstractmethod
    def to_json(self) -> dict[str, Any]:
        """Convert product data to a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the product.

        """

    @abstractmethod
    def download(self, path: Path, *, dependencies: bool = True) -> None:
        """Download the product to the given path using breadth-first traversal.

        Args:
            path: Path to download the product to.
            dependencies: Whether to download dependencies.

        """

    @abstractmethod
    def get_dependencies(self) -> "ProductCollection":
        """Get a ProductCollection containing this product and all its dependencies.

        Uses BFS traversal to collect all dependencies in the correct order.

        Returns:
            ProductCollection with BFS-ordered products.

        """

    @abstractmethod
    def update(self, path: Path, *, dependencies: bool = True) -> None:
        """Update the product in the workarea.

        Args:
            path: Path to update the product at.
            dependencies: Whether to update dependencies.

        """

    @abstractmethod
    def repair(self, path: Path, *, dependencies: bool = True) -> None:
        """Repair the product in the workarea.

        Args:
            path: Path to repair the product at.
            dependencies: Whether to repair dependencies.

        """

    def install(self, path: Path, *, dependencies: bool = True) -> None:
        """Install the product into the workarea.

        Args:
            path: Path to install the product to.
            dependencies: Whether to install dependencies.

        Raises:
            NotImplementedError: If the installable does not support installation.

        """
        msg = "Install is not implemented"
        raise NotImplementedError(msg)

    def uninstall(self, path: Path) -> None:
        """Uninstall the product from the workarea.

        Args:
            path: Path to uninstall the product from.

        Raises:
            NotImplementedError: If the installable does not support uninstallation.

        """
        msg = "Uninstall is not implemented"
        raise NotImplementedError(msg)

    def upgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Upgrade the product in the workarea.

        Args:
            path: Path to upgrade the product at.
            dependencies: Whether to upgrade dependencies.

        Raises:
            NotImplementedError: If the installable does not support upgrade.

        """
        msg = "Upgrade is not implemented"
        raise NotImplementedError(msg)

    def downgrade(self, path: Path, *, dependencies: bool = True) -> None:
        """Downgrade the product in the workarea.

        Args:
            path: Path to downgrade the product at.
            dependencies: Whether to downgrade dependencies.

        Raises:
            NotImplementedError: If the installable does not support downgrade.

        """
        msg = "Downgrade is not implemented"
        raise NotImplementedError(msg)

    def backup(self, path: Path) -> None:
        """Backup the product in the workarea.

        Args:
            path: Path to backup the product from.

        Raises:
            NotImplementedError: If the installable does not support backup.

        """
        msg = "Backup is not implemented"
        raise NotImplementedError(msg)

    def restore(self, path: Path) -> None:
        """Restore the product in the workarea.

        Args:
            path: Path to restore the product from.

        Raises:
            NotImplementedError: If the installable does not support restore.

        """
        msg = "Restore is not implemented"
        raise NotImplementedError(msg)

    def delete(self, path: Path) -> None:
        """Delete the product in the workarea.

        Args:
            path: Path to delete the product from.

        Raises:
            NotImplementedError: If the installable does not support deletion.

        """
        msg = "Delete is not implemented"
        raise NotImplementedError(msg)
