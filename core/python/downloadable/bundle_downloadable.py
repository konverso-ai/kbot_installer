"""BundleDownloadable for downloading products from a bundle descriptor."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typing_extensions import override

from downloadable.base import DownloadableBase
from downloadable.product_downloadable import ProductDownloadable
from git.provider.storage_provider import StorageProvider
from installer_support.installation_table import InstallationTable
from storage.factory import add_storage
from utils.bundle import Bundle
from utils.Logger import logger
from writer.factory import add_writer

if TYPE_CHECKING:
    from pathlib import Path

    from storage.base import StorageBackendEnum, StorageBase

log = logger.get_package_logger("installable")


class BundleDownloadable(DownloadableBase):
    """Orchestrate downloading every product declared by a Bundle from storage."""

    __bundle: Bundle
    __bundle_storage: StorageBase
    __artifact_storage: StorageBase
    __table: InstallationTable
    __storage_backend: str
    __provider: StorageProvider

    def __init__(
        self,
        storage_name: StorageBackendEnum,
        name: str,
        installer_dir: Path,
        *,
        verbose: bool = False,
    ) -> None:
        """Initialize the installable by fetching the bundle descriptor.

        Args:
            storage_name: Storage backend holding the bundle descriptor and artifacts.
            name: Name of the bundle to fetch.
            installer_dir: Directory the bundle descriptor is cached into.
            verbose: Whether to enable verbose logging.

        """
        self.__storage_backend = storage_name.value
        self.__bundle_storage = add_storage(
            name=storage_name.value, container_name="bundles"
        )
        self.__artifact_storage = add_storage(
            name=storage_name.value, container_name="artifacts"
        )
        self.__table = InstallationTable(verbose=verbose)
        self.__bundle = self._get_bundle(name=name, path=installer_dir)
        self.__provider = StorageProvider(storage=self.__artifact_storage)

    def _get_bundle(self, name: str, path: Path) -> Bundle:
        """Fetch the bundle descriptor from storage and cache it locally.

        Args:
            name: Name of the bundle to fetch.
            path: Directory the descriptor is cached into.

        Returns:
            The resolved bundle descriptor.

        Raises:
            ValueError: If the bundle descriptor cannot be found in storage.

        """
        bundle_content = self.__bundle_storage.get(str(Bundle.file_name(name)))
        if bundle_content is None:
            msg = f"Bundle {name} was not found"
            raise ValueError(msg)
        bundle = Bundle.from_json(json.loads(bundle_content))
        add_writer("text").write(
            bundle_content, path / Bundle.file_name(bundle.name, bundle.version)
        )
        return bundle

    @override
    def download(self, path: Path) -> None:
        """Download every product declared by the bundle into path.

        Products already present at the pinned commit are left untouched.

        Args:
            path: Directory that will contain the downloaded products.

        """
        for product in self.__bundle.versions:
            ProductDownloadable(
                product=product,
                provider=self.__provider,
                table=self.__table,
                include_dependencies=False,
            ).download(path)
