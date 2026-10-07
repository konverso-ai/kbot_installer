"""BundleDownloadable for downloading products from a bundle descriptor."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typing_extensions import override

from downloadable.base import DownloadableBase
from downloadable.product_downloadable import ProductDownloadable
from git.provider.factory import build_configured_storage
from git.provider.storage_provider import StorageProvider
from installer_support.installation_table import InstallationTable
from utils.bundle import Bundle
from utils.Logger import logger
from utils.version import Version
from writer.factory import add_writer

if TYPE_CHECKING:
    from pathlib import Path

    from storage.base import StorageBackendEnum, StorageBase

log = logger.get_package_logger("installable")

# Fixed name the bundle descriptor is cached under locally, mirroring the
# product convention of a fixed "description.xml"/"description.json" name
# per install location rather than a name+version-derived one.
LOCAL_BUNDLE_FILE_NAME = "bundle.json"


def find_latest_bundle_name(storage: StorageBase, name: str, version: Version) -> str:
    """Find the latest published bundle named name for the ``major.minor`` of version.

    Only top-level ``<name>-<version>.json`` descriptors are considered;
    versions are compared once parsed (``2025.3.0018`` > ``2025.03.0016``).

    Args:
        storage: Storage scoped to the ``bundles`` area.
        name: Bundle name, without version (e.g. ``ev-basic``).
        version: Version whose ``major.minor`` the bundle must match.

    Returns:
        The storage key stem of the latest bundle, i.e. the ``name`` to pass
        to :class:`BundleDownloadable`.

    Raises:
        ValueError: If no bundle with that name and ``major.minor`` exists.

    """
    prefix = f"{name}-"
    candidates: list[tuple[Version, str]] = []
    for key in storage.list(""):
        if "/" in key or not key.endswith(".json"):
            continue
        stem = key.removesuffix(".json")
        if not stem.startswith(prefix):
            continue
        try:
            candidate_version = Version.parse(stem.removeprefix(prefix))
        except (ValueError, TypeError):
            continue
        if not candidate_version:
            continue
        if (candidate_version.major, candidate_version.minor) == (version.major, version.minor):
            candidates.append((candidate_version, stem))
    if not candidates:
        msg = f"No bundle '{name}' {version.major}.{version.minor:02d}.* found in storage"
        raise ValueError(msg)
    return max(candidates, key=lambda candidate: candidate[0])[1]


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
        table: InstallationTable | None = None,
    ) -> None:
        """Initialize the installable by fetching the bundle descriptor.

        Args:
            storage_name: Storage backend holding the bundle descriptor and artifacts.
            name: Name of the bundle to fetch.
            installer_dir: Directory the bundle descriptor is cached into.
            verbose: Whether to enable verbose logging; ignored when table is given.
            table: Table the downloads are reported to. Defaults to a new table.

        """
        self.__storage_backend = storage_name.value
        self.__bundle_storage = build_configured_storage(
            storage_name.value, area="bundles"
        )
        self.__artifact_storage = build_configured_storage(
            storage_name.value, area="artifacts"
        )
        self.__table = table or InstallationTable(verbose=verbose)
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
        add_writer("text").write(bundle_content, path / LOCAL_BUNDLE_FILE_NAME)
        return bundle

    @override
    def download(self, path: Path) -> None:
        """Download every product declared by the bundle into path.

        Products already present at the pinned commit are left untouched.

        Args:
            path: Directory that will contain the downloaded products.

        """
        self.__table.fit_product_names(product.name for product in self.__bundle.versions)
        for product in self.__bundle.versions:
            ProductDownloadable(
                product=product,
                provider=self.__provider,
                table=self.__table,
                include_dependencies=False,
            ).download(path)
