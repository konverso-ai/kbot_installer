"""InstallerUpgradable: move the products of an installer directory to a newer release.

The target is either an installed product with its dependency closure
(``product`` + ``version``) or a bundle (an exact bundle name, or the latest
bundle of the installed bundle's name for ``version``). :meth:`InstallerUpgradable.check`
validates the installer without modifying it; :meth:`InstallerUpgradable.apply`
then checks out the git working copies on the release branch, replaces the
storage downloads, and removes the products the new target no longer needs.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from downloadable.bundle_downloadable import (
    LOCAL_BUNDLE_FILE_NAME,
    BundleDownloadable,
    find_latest_bundle_name,
)
from downloadable.factory import build_downloadable
from downloadable.product_downloadable import (
    LOCAL_BUILD,
    LOCAL_GIT_WORKING_COPY,
    LOCAL_SYMLINK,
    ProductDownloadable,
)
from git.provider.factory import build_configured_storage
from git.versioner.errors import DetachedHeadError, VersionerError
from git.versioner.factory import add_versioner_for_repository_remote
from installable.dependency_graph import DependencyGraph
from installer_support.installer_service import InstallerService
from installer_support.installer_utils import version_to_branch
from updatable.installer_updatable import format_uncommitted_changes
from upgradable.errors import UpgradeError
from utils.bundle import Bundle
from utils.Logger import logger
from utils.version import Version

if TYPE_CHECKING:
    from pathlib import Path

    from git.versioner.base import VersionerBase
    from storage.base import StorageBackendEnum
    from utils.product.product import Product

log = logger.get_package_logger("upgradable")


@dataclass(frozen=True)
class UpgradeOutcome:
    """Products added to and removed from the installer by an upgrade.

    Attributes:
        added: Product folder names new in the installer.
        removed: Product folder names no longer in the installer.
        moved_dir: Folder the removed git working copies were moved to, None if none was.

    """

    added: list[str]
    removed: list[str]
    moved_dir: Path | None


class InstallerUpgradable:
    """Upgrade the products of an installer directory to a newer release.

    Modes: ``bundle`` set → upgrade to that exact bundle; else ``product`` set →
    upgrade ``product`` and its dependencies to ``version``; else → upgrade to the
    latest bundle of the installed bundle's name for ``version``.

    Attributes:
        installer_path: Installer directory holding the products.
        target: Human-readable description of the upgrade target, set by :meth:`check`.

    """

    def __init__(
        self,
        installer_path: Path,
        storage_backend: StorageBackendEnum,
        *,
        product: str | None = None,
        version: str | None = None,
        bundle: str | None = None,
        provider: tuple[str, ...] = (),
        verbose: bool = False,
    ) -> None:
        """Initialize the upgrade.

        Args:
            installer_path: Installer directory holding the products.
            storage_backend: Storage backend for bundles and storage downloads.
            product: Product to upgrade with its dependencies (product mode).
            version: Target version (e.g. ``2026.01``); unused when ``bundle`` is set.
            bundle: Exact bundle descriptor name to upgrade to.
            provider: Providers to download products with in product mode; empty for the default order.
            verbose: Whether to enable verbose logging.

        """
        self.installer_path = installer_path
        self.storage_backend = storage_backend
        self.product = product
        self.version = version
        self.bundle = bundle
        self.provider = provider
        self.verbose = verbose
        self.target = ""
        self._entries: list[tuple[Path, Product]] = []
        self._branch: str | None = None
        self._bundle_name: str | None = None
        self._bundle_products: set[str] | None = None
        self._versioners: dict[Path, VersionerBase] = {}

    @property
    def _product_mode(self) -> bool:
        return not self.bundle and bool(self.product)

    def check(self) -> None:
        """Check the installer can be upgraded, without modifying it.

        Every problem is collected before failing: unknown product or bundle,
        target not newer, symlinked or locally built products, git working
        copies with uncommitted changes or without the release branch.

        Raises:
            UpgradeError: If the installer is not ready for the upgrade.

        """
        self._entries = InstallerService(self.installer_path).load_product_dirs()
        problems: list[str] = []
        if self._product_mode:
            self._resolve_product_target(problems)
        else:
            self._resolve_bundle_target(problems)

        for path, product in self._entries:
            kind = ProductDownloadable.local_copy_kind(path)
            if kind in (LOCAL_SYMLINK, LOCAL_BUILD):
                problems.append(
                    f"{path.name}: {kind} cannot be upgraded (only storage downloads and git working copies can)"
                )
            elif kind == LOCAL_GIT_WORKING_COPY:
                problem = self._check_git_working_copy(path, product)
                if problem:
                    problems.append(f"{path.name}: {problem}")

        if problems:
            msg = "Installer is not ready for the upgrade:\n" + "\n".join(f"  - {p}" for p in problems)
            raise UpgradeError(msg)

    def _resolve_product_target(self, problems: list[str]) -> None:
        """Resolve the release branch of product mode and check the product is upgraded.

        Args:
            problems: List the problems found are appended to.

        """
        version = self.version or ""
        bare_version = version.removesuffix("-dev")
        try:
            target = Version.parse(bare_version)
        except (ValueError, TypeError):
            problems.append(f"Invalid version '{version}'")
            return
        installed = next((p for _, p in self._entries if p.name == self.product), None)
        if installed is None:
            problems.append(f"Product '{self.product}' is not installed in '{self.installer_path}'")
        elif installed.version and (target.major, target.minor) <= (installed.version.major, installed.version.minor):
            problems.append(f"'{self.product}' is at version {installed.version.to_json_str()}: {version} is not newer")
        self._branch = version_to_branch(version)
        self.target = f"product {self.product} {bare_version} (branch {self._branch})"

    def _resolve_bundle_target(self, problems: list[str]) -> None:
        """Resolve the bundle to upgrade to and its release branch.

        The descriptor is read from storage directly: ``BundleDownloadable``
        would overwrite the cached ``bundle.json`` before the upgrade is confirmed.

        Args:
            problems: List the problems found are appended to.

        """
        storage = build_configured_storage(self.storage_backend.value, area="bundles")
        bundle_json = self.installer_path / LOCAL_BUNDLE_FILE_NAME
        current = Bundle.from_json(bundle_json.read_text(encoding="utf-8")) if bundle_json.is_file() else None

        name = self.bundle
        if not name:
            if current is None:
                problems.append(f"No '{LOCAL_BUNDLE_FILE_NAME}' in '{self.installer_path}': not a bundle install")
                return
            version = self.version or ""
            try:
                name = find_latest_bundle_name(storage, current.name, Version.parse(version.removesuffix("-dev")))
            except (ValueError, TypeError) as e:
                problems.append(str(e))
                return

        content = storage.get(str(Bundle.file_name(name)))
        if content is None:
            problems.append(f"Bundle '{name}' was not found in storage")
            return
        new = Bundle.from_json(json.loads(content))
        if current and (new.version.major, new.version.minor) <= (current.version.major, current.version.minor):
            problems.append(
                f"Bundle {name} is not newer than the installed {current.name} {current.version.to_json_str()}"
            )
        self._branch = version_to_branch(f"{new.version.major}.{new.version.minor:02d}")
        self._bundle_name = name
        self._bundle_products = {p.name for p in new.versions}
        self.target = f"bundle {name} (branch {self._branch})"

    def _is_upgraded_git_copy(self, product: Product) -> bool:
        """Tell whether a git working copy of product is moved to the release branch.

        In product mode the new dependency closure is only known once the new
        branches are checked out, so every working copy is moved.

        """
        if self._product_mode:
            return True
        return self._bundle_products is not None and product.name in self._bundle_products

    def _check_git_working_copy(self, path: Path, product: Product) -> str | None:
        """Check a git working copy is clean and has the release branch.

        Args:
            path: Working copy folder.
            product: Product described by the working copy.

        Returns:
            The problem found, or None if the working copy can be upgraded.

        """
        try:
            versioner = add_versioner_for_repository_remote(path)
            changed = versioner.status(path).changed
            if changed:
                return format_uncommitted_changes(changed)
            self._versioners[path] = versioner
            if self._branch is None or not self._is_upgraded_git_copy(product):
                return None
            versioner.fetch(path)
            if versioner.select_branch(path, [self._branch]) is None:
                return f"branch '{self._branch}' not found locally or on origin"
        except (VersionerError, ValueError, OSError) as e:
            return str(e)
        return None

    def apply(self) -> UpgradeOutcome:
        """Move the installer to the target checked by :meth:`check`.

        Git working copies are checked out on the release branch and pulled;
        storage downloads are deleted then downloaded again from the new target;
        products outside the new target are removed (git working copies are
        moved to ``.removed_<timestamp>/``, other folders deleted).

        Returns:
            The products added and removed.

        Raises:
            UpgradeError: If :meth:`check` did not resolve a target.

        """
        if self._branch is None:
            msg = "The upgrade target is not resolved: run check() first"
            raise UpgradeError(msg)
        branch = self._branch
        timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        old_names = {path.name for path, _ in self._entries}

        for path, product in self._entries:
            kind = ProductDownloadable.local_copy_kind(path)
            if kind == LOCAL_GIT_WORKING_COPY and self._is_upgraded_git_copy(product):
                self._checkout_release_branch(path, branch)
            elif kind is None:
                log.info("Removing %s before downloading its new version", path.name)
                shutil.rmtree(path)

        if self._product_mode:
            build_downloadable(
                product=self.product or "",
                version=self.version,
                bundle=None,
                installer_path=self.installer_path,
                provider=self.provider,
                storage_backend=self.storage_backend,
                include_dependencies=True,
                verbose=self.verbose,
            ).download(self.installer_path)
        else:
            BundleDownloadable(
                storage_name=self.storage_backend,
                name=self._bundle_name or "",
                installer_dir=self.installer_path,
                verbose=self.verbose,
            ).download(self.installer_path)

        moved_dir = self._remove_products_outside_target(timestamp)
        new_names = {path.name for path, _ in InstallerService(self.installer_path).load_product_dirs()}
        return UpgradeOutcome(
            added=sorted(new_names - old_names),
            removed=sorted(old_names - new_names),
            moved_dir=moved_dir,
        )

    def _checkout_release_branch(self, path: Path, branch: str) -> None:
        """Check out a git working copy on branch, then pull it.

        Args:
            path: Working copy folder.
            branch: Release branch to move to.

        """
        versioner = self._versioners.get(path) or add_versioner_for_repository_remote(path)
        try:
            current: str | None = versioner.current_branch(path)
        except DetachedHeadError:
            current = None
        if current != branch:
            versioner.checkout(path, branch)
        versioner.pull(path, branch)
        log.info("Checked out %s on %s", path.name, branch)

    def _remove_products_outside_target(self, timestamp: str) -> Path | None:
        """Remove the installed products the new target does not need.

        Args:
            timestamp: Suffix of the folder removed git working copies are moved to.

        Returns:
            The folder removed git working copies were moved to, or None if none was.

        """
        entries = InstallerService(self.installer_path).load_product_dirs()
        if self._product_mode:
            graph = DependencyGraph([p for _, p in entries])
            targets = {self.product, *graph.get_transitive_dependencies(self.product or "")}
        else:
            targets = self._bundle_products or set()

        moved_dir: Path | None = None
        for path, product in entries:
            if product.name in targets:
                continue
            if ProductDownloadable.local_copy_kind(path) == LOCAL_GIT_WORKING_COPY:
                moved_dir = self.installer_path / f".removed_{timestamp}"
                moved_dir.mkdir(exist_ok=True)
                path.rename(moved_dir / path.name)
                log.info("Moved %s, no longer needed, to %s", path.name, moved_dir)
            else:
                shutil.rmtree(path)
                log.info("Removed %s, no longer needed", path.name)
        return moved_dir
