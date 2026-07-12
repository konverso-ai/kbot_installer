"""Download a single product archive pinned to a specific commit."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from installer_support.installation_table import InstallationTable
from storage.base import StorageBase
from utils.Logger import logger
from utils.product import Product

log = logger.getPackageLogger("installable")


class StoragePinnedProductInstallable:
    """Download and extract one product archive from storage at a pinned commit."""

    def __init__(
        self,
        product: Product,
        installer_dir: Path,
        storage: StorageBase,
        installation_table: InstallationTable,
        storage_backend: str,
    ) -> None:
        """Initialize a pinned product download.

        Args:
            product: Product descriptor from a bundle with build metadata.
            installer_dir: Directory that will contain downloaded products.
            storage: Storage backend used to fetch the archive.
            installation_table: Table used to report download progress.
            storage_backend: Active storage backend name for display labels.

        """
        self.product = product
        self.installer_dir = installer_dir
        self.storage = storage
        self.installation_table = installation_table
        self.storage_backend = storage_backend

    @staticmethod
    def build_storage_key(product: Product) -> str:
        """Build the storage key for a pinned product archive.

        Args:
            product: Product descriptor with build branch and commit.

        Returns:
            Object key for the product archive in storage.

        Raises:
            ValueError: If build metadata is incomplete.

        """
        if not product.build or not product.build.branch or not product.build.commit:
            msg = f"Product '{product.name}' has incomplete build metadata in bundle"
            raise ValueError(msg)
        return (
            f"{product.build.branch}/{product.name}/"
            f"{product.name}_{product.build.commit}.tar.gz"
        )

    def download(self) -> None:
        """Download and extract the pinned product archive into the installer directory."""
        key = self.build_storage_key(self.product)
        provider_label = f"storage ({self.storage_backend})"
        product_dir = self.installer_dir / self.product.name

        self.installation_table.begin_installation(self.product.name)
        try:
            if product_dir.exists():
                shutil.rmtree(product_dir)

            log.info(
                "Downloading product '%s' from storage (key: %s)",
                self.product.name,
                key,
            )
            self.storage.download(key, str(self.installer_dir))

            nexus_path = product_dir / "nexus.json"
            nexus_path.write_text(
                json.dumps(self.product.to_json(), indent=2),
                encoding="utf-8",
            )

            self.installation_table.complete_installation(
                product_name=self.product.name,
                provider_name=provider_label,
                status="success",
            )
        except Exception as exc:
            self.installation_table.complete_installation(
                product_name=self.product.name,
                provider_name=provider_label,
                status="error",
                error_message=str(exc),
            )
            raise
