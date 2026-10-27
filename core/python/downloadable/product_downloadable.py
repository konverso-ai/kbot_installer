"""ProductDownloadable for downloading a product and its dependencies."""

import shutil
from collections import deque
from pathlib import Path

from typing_extensions import override

from downloadable.base import DownloadableBase
from git.provider.base import ProviderBase
from installer_support.installation_table import InstallationTable
from utils.Logger import logger
from utils.path_utils import ensure_directory
from utils.product.product import Product

log = logger.get_package_logger("downloadable")

LOCAL_SYMLINK = "local symlink"
LOCAL_GIT_WORKING_COPY = "local git working copy"
LOCAL_BUILD = "local build"


class ProductDownloadable(DownloadableBase):
    """Orchestrate downloading a Product through a ProviderBase.

    A product already present in the target installer folder is skipped when
    up to date, and removed then downloaded again when outdated (e.g. after a
    version change). User-managed copies (manual builds, git working copies,
    symlinks) are never replaced: see `local_copy_kind`.
    """

    __product: Product
    __provider: ProviderBase
    __include_dependencies: bool
    __table: InstallationTable

    def __init__(
        self,
        product: Product,
        provider: ProviderBase,
        table: InstallationTable | None = None,
        *,
        include_dependencies: bool = True,
    ) -> None:
        """Initialize the installable.

        Args:
            product: Product to download.
            provider: Provider used to clone the product (and its dependencies).
            include_dependencies: Whether download() should also fetch dependencies.
            table: InstallationTable to track downloaded products.

        """
        self.__product = product
        self.__provider = provider
        self.__include_dependencies = include_dependencies
        self.__table = table or InstallationTable()

    @override
    def download(self, path: Path) -> None:
        """Download the product into path.

        Args:
            path: Directory that will contain the downloaded product(s).

        """
        path = ensure_directory(path=path)
        if self.__include_dependencies:
            self._download_with_dependencies(path)
        else:
            self._download_without_dependencies(self.__product, path / self.__product.name)

    def _download_without_dependencies(self, product: Product, path: Path) -> None:
        """Clone product into path, unless it is already up to date or user-managed.

        When the product pins a commit, the product is re-downloaded whenever
        the commit recorded in the existing ``description.json`` no longer
        matches; the outdated folder is removed first. User-managed copies (see
        `local_copy_kind`) are always kept, even when outdated.

        Args:
            product: Product to clone.
            path: Directory the product should be cloned into.

        Raises:
            ValueError: If the product has no build information to clone from.

        """
        self.__table.begin_installation(product.name)
        pinned_commit = product.build.commit if product.build else None
        local_copy = self.local_copy_kind(path)
        if local_copy is not None:
            details = f"Kept {local_copy}"
            if pinned_commit and not self._is_up_to_date(path, pinned_commit):
                details += f" (expected commit {pinned_commit[:10]})"
                log.warning("Keeping %s '%s' instead of downloading commit %s.", local_copy, path, pinned_commit)
            self.__table.complete_installation(
                product_name=product.name,
                provider_name="local",
                status="kept",
                details=details,
            )
            return
        if self._is_up_to_date(path, pinned_commit):
            self.__table.complete_installation(
                product_name=product.name,
                provider_name=f"{self.__provider.get_name()} (cached)",
                status="skipped",
            )
            return
        if product.build is None:
            msg = "Product build information is not available"
            self.__table.complete_installation(
                product_name=product.name,
                provider_name=self.__provider.get_name(),
                status="error",
                error_message=msg,
            )
            raise ValueError(msg)
        if path.exists():
            # Stale download (e.g. a previous version): start from a clean folder
            # so files removed in the new version don't linger.
            log.info("Removing outdated '%s' before downloading it again.", path)
            shutil.rmtree(path)
        self.__provider.clone_and_checkout(
            path.name,
            path,
            branch=product.build.branch,
            commit_id=pinned_commit or None,
        )
        self.__table.complete_installation(
            product_name=product.name,
            provider_name=self.__provider.get_name(),
            status="success",
        )

    @staticmethod
    def local_copy_kind(path: Path) -> str | None:
        """Tell whether path holds a user-managed copy the installer must never replace.

        Such copies are left untouched even when outdated, since replacing them
        would delete the user's work:

        - a symbolic link (e.g. to a repository under ``~/dev/git``);
        - a git working copy (it may hold uncommitted changes);
        - a manual build: ``make`` in ``~/dev/git/<product>`` copies the product
          into the installer folder and removes its ``description.json``
          (Makefile ``finish`` target), whereas every storage download has one.

        Args:
            path: Directory the product would be downloaded into.

        Returns:
            ``LOCAL_SYMLINK``, ``LOCAL_GIT_WORKING_COPY`` or ``LOCAL_BUILD``, or
            None if path is absent or holds a regular download that may be replaced.

        """
        if path.is_symlink():
            return LOCAL_SYMLINK
        if not path.is_dir():
            return None
        if (path / ".git").exists():
            return LOCAL_GIT_WORKING_COPY
        if (path / "description.xml").exists() and not (path / "description.json").exists():
            return LOCAL_BUILD
        return None

    @staticmethod
    def _is_up_to_date(path: Path, pinned_commit: str | None) -> bool:
        """Check whether path already holds the product at the pinned commit.

        Args:
            path: Directory the product would be downloaded into.
            pinned_commit: Commit the product is pinned to, or None/"" if the
                product is not pinned (any existing download is considered current).

        Returns:
            True if path is already populated with the expected content.

        """
        if not (path / "description.xml").exists():
            return False
        if not pinned_commit:
            return True
        description_json = path / "description.json"
        if not description_json.exists():
            return False
        existing_product = Product.from_json_file(description_json)
        return existing_product.build is not None and existing_product.build.commit == pinned_commit

    def _download_with_dependencies(self, path: Path) -> None:
        """Download the product and its dependencies using breadth-first traversal.

        Every product in the dependency graph is cloned on the same branch as the
        main product; only the main product's own commit (if pinned) is honored,
        since parent references carry no build metadata of their own. Products
        already present in path are left untouched; their description.xml is only
        read to discover further dependencies.

        Args:
            path: Path to the directory that will contain the downloaded products.

        """
        processed: set[str] = set()
        queue: deque[str] = deque([self.__product.name])
        main_build = self.__product.build

        while queue:
            name = queue.popleft()
            if name in processed:
                continue
            processed.add(name)

            product_path = path / name
            product_to_clone = self.__product if name == self.__product.name else Product(name=name, build=main_build)
            self._download_without_dependencies(product_to_clone, product_path)

            product = self._get_product(path, name)
            if name == self.__product.name:
                self.__product = product

            queue.extend(parent_name for parent_name in product.parent_names if parent_name not in processed)
            # Size the product column for the names discovered so far, before printing their rows.
            self.__table.fit_product_names(queue)

    def _get_product(self, path: Path, name: str) -> Product:
        """Load the product description from its downloaded folder.

        Merges description.xml with description.json when both are present.

        Args:
            path: Base directory containing the downloaded products.
            name: Name of the product to load.

        Returns:
            The resolved product description.

        Raises:
            ValueError: If description.xml is missing in the product's folder.

        """
        product_path = path / name
        description_xml = product_path / "description.xml"
        if not description_xml.exists():
            self.__table.complete_installation(
                product_name=name,
                provider_name=self.__provider.get_name(),
                status="error",
                error_message=f"description.xml not found in {product_path}",
            )
            msg = f"description.xml not found in {product_path}"
            raise ValueError(msg)

        xml_product = Product.from_xml_file(description_xml)

        description_json = product_path / "description.json"
        if not description_json.exists():
            return xml_product

        json_product = Product.from_json_file(description_json)
        return Product.merge(xml_product, json_product)
