"""BundleInstallable for downloading products from a bundle descriptor."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator
from typing_extensions import Self

from installable.storage_pinned_product import StoragePinnedProductInstallable
from installer_support.installation_table import InstallationTable
from installer_support.installer_utils import ensure_directory
from storage.base import StorageBase
from utils.bundle import Bundle
from utils.product import Product

logger = logging.getLogger(__name__)


class BundleInstallable(BaseModel):
    """Installable backed by a bundle descriptor in object storage."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bundle_name: str
    bundle_version: str
    top_product: str
    installer_dir: Path
    storage: StorageBase
    installation_table: InstallationTable
    storage_backend: str
    verbose: bool = False
    bundle: Bundle | None = None

    @model_validator(mode="before")
    @classmethod
    def _load_bundle_descriptor(cls, data: object) -> object:
        """Fetch the bundle descriptor when only storage coordinates are provided."""
        if not isinstance(data, dict) or data.get("bundle") is not None:
            return data

        bundle_name = data.get("bundle_name")
        bundle_version = data.get("bundle_version")
        top_product = data.get("top_product")
        storage = data.get("storage")
        if not (
            isinstance(bundle_name, str)
            and bundle_name
            and isinstance(bundle_version, str)
            and bundle_version
            and isinstance(top_product, str)
            and top_product
        ):
            return data
        if not isinstance(storage, StorageBase):
            return data

        bundle = cls._fetch_bundle(storage, bundle_name, bundle_version)
        if cls._find_bundle_product(bundle, top_product) is None:
            msg = (
                f"Product '{top_product}' not found in bundle "
                f"'{bundle_name}' version '{bundle_version}'"
            )
            raise ValueError(msg)

        payload = dict(data)
        payload["bundle"] = bundle
        payload["installer_dir"] = Path(payload["installer_dir"])
        return payload

    @model_validator(mode="after")
    def _ensure_bundle_loaded(self) -> Self:
        """Ensure the bundle descriptor is available after validation."""
        if self.bundle is None:
            msg = "Bundle descriptor is required"
            raise ValueError(msg)
        return self

    @classmethod
    def from_storage(
        cls,
        bundle_name: str,
        bundle_version: str,
        top_product: str,
        installer_dir: str | Path,
        storage: StorageBase,
        installation_table: InstallationTable,
        storage_backend: str,
        *,
        verbose: bool = False,
    ) -> BundleInstallable:
        """Fetch a bundle descriptor from storage and build the installable.

        Args:
            bundle_name: Name of the bundle.
            bundle_version: Version of the bundle.
            top_product: Root product defining the highest installation level.
            installer_dir: Directory that will contain downloaded products.
            storage: Storage backend used to fetch bundle and product archives.
            installation_table: Table used to report download progress.
            storage_backend: Active storage backend name for display labels.
            verbose: When True, emit detailed log output.

        Returns:
            Configured bundle installable.

        Raises:
            ValueError: If the bundle or top product cannot be resolved.

        """
        return cls(
            bundle_name=bundle_name,
            bundle_version=bundle_version,
            top_product=top_product,
            installer_dir=Path(installer_dir),
            storage=storage,
            installation_table=installation_table,
            storage_backend=storage_backend,
            verbose=verbose,
        )

    def download(self, *, dependencies: bool = True) -> None:
        """Download pinned products from the bundle into the installer directory.

        Args:
            dependencies: Whether to download parent dependencies.

        """
        bundle = self.bundle
        assert bundle is not None
        logger.info(
            "Installing bundle '%s' version '%s' from product '%s' (dependencies: %s)",
            self.bundle_name or bundle.name,
            self.bundle_version or bundle.version.to_str(),
            self.top_product,
            dependencies,
        )

        ensure_directory(self.installer_dir)
        self._download_products_recursively(
            self.top_product,
            include_dependencies=dependencies,
        )

        logger.info(
            "Bundle installation completed for product '%s'",
            self.top_product,
        )

    @staticmethod
    def _bundle_storage_key(bundle_name: str, bundle_version: str) -> str:
        """Build the primary storage key for a bundle descriptor."""
        return f"{bundle_name}-{bundle_version}.json"

    @staticmethod
    def _fetch_bundle(
        storage: StorageBase,
        bundle_name: str,
        bundle_version: str,
    ) -> Bundle:
        """Fetch and parse a bundle descriptor from storage."""
        candidate_keys = [
            BundleInstallable._bundle_storage_key(bundle_name, bundle_version),
            f"{bundle_name}.json",
        ]
        for key in candidate_keys:
            content = storage.get(key)
            if content:
                logger.info("Loaded bundle descriptor from storage key '%s'", key)
                return Bundle.from_json(content)

        msg = (
            f"Bundle '{bundle_name}' version '{bundle_version}' "
            "was not found in storage"
        )
        raise ValueError(msg)

    @staticmethod
    def _find_bundle_product(bundle: Bundle, product_name: str) -> Product | None:
        """Return a product entry from a bundle by name."""
        for product in bundle.versions:
            if product.name == product_name:
                return product
        return None

    def _get_installed_bundle_commit(self, product_name: str) -> str | None:
        """Return the commit recorded in a product's ``nexus.json`` stamp file."""
        nexus_json = self.installer_dir / product_name / "nexus.json"
        if not nexus_json.exists():
            return None
        try:
            data = json.loads(nexus_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        build = data.get("build")
        if not isinstance(build, dict):
            return None
        commit = build.get("commit")
        return commit if isinstance(commit, str) else None

    @staticmethod
    def _is_product_installed(installer_dir: Path, product_name: str) -> bool:
        """Check whether a product directory exists and is non-empty."""
        product_dir = installer_dir / product_name
        return product_dir.exists() and any(product_dir.iterdir())

    def _download_pinned_product(self, product: Product) -> None:
        """Download one pinned product archive from storage."""
        StoragePinnedProductInstallable(
            product=product,
            installer_dir=self.installer_dir,
            storage=self.storage,
            installation_table=self.installation_table,
            storage_backend=self.storage_backend,
        ).download()

    def _download_products_recursively(
        self,
        product_name: str,
        *,
        include_dependencies: bool,
        visited: set[str] | None = None,
    ) -> None:
        """Recursively download bundle products and their parents."""
        if visited is None:
            visited = set()
        if product_name in visited:
            return
        visited.add(product_name)

        bundle = self.bundle
        assert bundle is not None
        bundle_product = self._find_bundle_product(bundle, product_name)
        if bundle_product is not None:
            installed_commit = self._get_installed_bundle_commit(product_name)
            bundle_commit = (
                bundle_product.build.commit if bundle_product.build else None
            )
            needs_download = (
                not self._is_product_installed(
                    self.installer_dir,
                    product_name,
                )
                or installed_commit != bundle_commit
            )

            if include_dependencies:
                for parent_name in bundle_product.parent_names:
                    self._download_products_recursively(
                        parent_name,
                        include_dependencies=True,
                        visited=visited,
                    )

            if needs_download:
                self._download_pinned_product(bundle_product)
            else:
                self.installation_table.complete_installation(
                    product_name=product_name,
                    provider_name=f"storage ({self.storage_backend}) (cached)",
                    status="skipped",
                )
            return

        product_dir = self.installer_dir / product_name
        description_xml = product_dir / "description.xml"
        if description_xml.exists():
            if not include_dependencies:
                return
            local_product = Product.from_xml_file(description_xml)
            for parent_name in local_product.parent_names:
                self._download_products_recursively(
                    parent_name,
                    include_dependencies=True,
                    visited=visited,
                )
            return

        msg = (
            f"Product '{product_name}' was not found in the bundle "
            "and is not installed locally"
        )
        raise ValueError(msg)
