"""InstallerUpdatable: update the products of an installer directory in place.

Git working copies are checked out on the branch of their product version and
pulled. The other products are refreshed from storage: a bundle install moves to
the latest bundle of the same name and ``major.minor``, any other install
downloads the latest artifact of each product's build branch, unless the
description published next to it shows the installed commit. Products left
unchanged are reported as up to date.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from downloadable.bundle_downloadable import (
    LOCAL_BUNDLE_FILE_NAME,
    BundleDownloadable,
    find_latest_bundle_name,
)
from downloadable.product_downloadable import (
    LOCAL_BUILD,
    LOCAL_GIT_WORKING_COPY,
    LOCAL_SYMLINK,
    ProductDownloadable,
)
from git.provider.errors import ProviderError
from git.provider.factory import build_configured_storage, build_storage_provider
from git.versioner.errors import DetachedHeadError, VersionerError
from git.versioner.factory import add_versioner_for_repository_remote
from installer_support.installation_table import InstallationTable
from installer_support.installer_service import InstallerService
from installer_support.installer_utils import version_to_branch
from utils.bundle import Bundle
from utils.Logger import logger
from utils.product.product import Product

if TYPE_CHECKING:
    from git.provider.storage_provider import StorageProvider
    from git.versioner.base import VersionerBase
    from storage.base import StorageBackendEnum

log = logger.get_package_logger("updatable")

_GIT_PROVIDER_NAME = "git"
_STORAGE_PROVIDER_NAME = "storage"
_MAX_LISTED_CHANGES = 5


def _branch_candidates(product: Product) -> list[str]:
    """Return the branches a git working copy of product may be checked out on.

    Args:
        product: Product described by the working copy.

    Returns:
        The dev then prod release branches of the product version, or an empty
        list when the product has no version.

    """
    version = product.version.to_json_str()
    if not version:
        return []
    return list(dict.fromkeys([version_to_branch(version, "dev"), version_to_branch(version, "prod")]))


def _select_target_branch(versioner: VersionerBase, path: Path, product: Product, current: str | None) -> str:
    """Choose the branch a fetched git working copy must be pulled on.

    The current branch is kept when it is one of the version branches (or when
    the product has no version); otherwise the first version branch existing
    locally or on ``origin`` is chosen.

    Args:
        versioner: Versioner bound to the working copy's remote.
        path: Working copy folder.
        product: Product described by the working copy.
        current: Branch currently checked out, None on a detached HEAD.

    Returns:
        The branch to check out and pull.

    Raises:
        ValueError: If no branch can be chosen.

    """
    candidates = _branch_candidates(product)
    if not candidates:
        if current is None:
            msg = "Detached HEAD and no version in description.xml: cannot choose a branch"
            raise ValueError(msg)
        return current
    if current in candidates:
        return current
    selected = versioner.select_branch(path, candidates)
    if selected is None:
        msg = f"None of the branches {', '.join(candidates)} exists"
        raise ValueError(msg)
    return selected


def format_uncommitted_changes(changed: list[str]) -> str:
    """Describe the uncommitted changes of a git working copy.

    Args:
        changed: Staged and unstaged changed paths.

    Returns:
        ``"Uncommitted changes: a, b"``, listing at most a few paths followed by ``" (+N more)"``.

    """
    message = f"Uncommitted changes: {', '.join(changed[:_MAX_LISTED_CHANGES])}"
    if len(changed) > _MAX_LISTED_CHANGES:
        message += f" (+{len(changed) - _MAX_LISTED_CHANGES} more)"
    return message


class InstallerUpdatable:
    """Update every product of an installer directory.

    Failures are reported per product in the installation table; the other
    products are still updated.

    Attributes:
        installer_path: Installer directory holding the products.
        storage_backend: Storage backend holding bundles and artifacts.
        verbose: Whether to show skipped products and extra details.

    """

    def __init__(
        self,
        installer_path: Path,
        storage_backend: StorageBackendEnum,
        *,
        verbose: bool = False,
    ) -> None:
        """Bind the updatable to an installer directory and storage backend.

        Args:
            installer_path: Installer directory holding the products.
            storage_backend: Storage backend holding bundles and artifacts.
            verbose: Whether to show skipped products and extra details.

        """
        self.installer_path = installer_path
        self.storage_backend = storage_backend
        self.verbose = verbose
        self._storage_provider: StorageProvider | None = None

    def __call__(self) -> list[str]:
        """Update the git working copies, then the storage-backed products.

        Returns:
            Folder names of the products whose update failed.

        Raises:
            ValueError: If the installation comes from a bundle and no newer
                bundle descriptor can be resolved or fetched.

        """
        table = InstallationTable(verbose=self.verbose, show_unchanged=True)
        entries = InstallerService(self.installer_path).load_product_dirs()
        table.fit_product_names(path.name for path, _ in entries)
        failed: list[str] = []

        for path, product in entries:
            if ProductDownloadable.local_copy_kind(path) == LOCAL_GIT_WORKING_COPY and not self._update_git_repository(
                path, product, table
            ):
                failed.append(path.name)

        if (self.installer_path / LOCAL_BUNDLE_FILE_NAME).exists():
            self._update_bundle(table)
            return failed

        for path, product in entries:
            kind = ProductDownloadable.local_copy_kind(path)
            if kind is None and (path / "description.json").exists():
                if not self._update_storage_artifact(path, product, table):
                    failed.append(path.name)
            elif kind in (LOCAL_SYMLINK, LOCAL_BUILD):
                table.begin_installation(path.name)
                table.complete_installation(
                    product_name=path.name,
                    provider_name="local",
                    status="kept",
                    details=f"Kept {kind}",
                )
        return failed

    def _update_git_repository(self, path: Path, product: Product, table: InstallationTable) -> bool:
        """Check out a git working copy on its version branch, then pull it.

        A working copy with staged or unstaged changes is left untouched.

        Args:
            path: Working copy folder.
            product: Product described by the working copy.
            table: Table the outcome is reported to.

        Returns:
            True on success, False if the working copy could not be updated.

        """
        table.begin_installation(path.name)
        try:
            versioner = add_versioner_for_repository_remote(path)
            changed = versioner.status(path).changed
            if changed:
                return self._report_error(table, path, _GIT_PROVIDER_NAME, format_uncommitted_changes(changed))

            versioner.fetch(path)
            try:
                current: str | None = versioner.current_branch(path)
            except DetachedHeadError:
                current = None

            target = _select_target_branch(versioner, path, product, current)

            if target != current:
                versioner.checkout(path, target)
            result = versioner.pull(path, target)
        except (VersionerError, ValueError, OSError) as e:
            return self._report_error(table, path, _GIT_PROVIDER_NAME, str(e))

        if target == current and result.is_fast_forward_noop:
            table.complete_installation(
                product_name=path.name,
                provider_name=_GIT_PROVIDER_NAME,
                status="skipped",
                details=f"{target} already up to date",
            )
        else:
            old_commit = (result.old_commit_id or "")[:10]
            new_commit = (result.new_commit_id or "")[:10]
            table.complete_installation(
                product_name=path.name,
                provider_name=_GIT_PROVIDER_NAME,
                status="success",
                details=f"{target} {old_commit} → {new_commit}",
            )
        return True

    def _update_storage_artifact(self, path: Path, product: Product, table: InstallationTable) -> bool:
        """Replace a storage download with the latest artifact of its build branch.

        The artifact is not downloaded when the description published next to
        it shows the installed commit. Otherwise, the existing folder is kept
        until the new artifact is fully downloaded, and also when it turns out
        to hold the installed commit.

        Args:
            path: Product folder.
            product: Product described by the folder.
            table: Table the outcome is reported to.

        Returns:
            True on success, False if the product could not be updated.

        """
        table.begin_installation(path.name)
        branch = product.build.branch if product.build else ""
        old_commit = product.build.commit if product.build else ""
        try:
            if not branch:
                return self._report_error(table, path, _STORAGE_PROVIDER_NAME, "No build branch in description.json")
            if self._storage_provider is None:
                self._storage_provider = build_storage_provider(self.storage_backend)

            latest_build = self._storage_provider.get_latest_build(path.name, branch)
            if old_commit and latest_build is not None and latest_build.commit == old_commit:
                return self._report_up_to_date(table, path, branch, old_commit)

            # Download next to the products (same filesystem, so rename works);
            # without a top-level description.xml, product discovery ignores it.
            with tempfile.TemporaryDirectory(dir=self.installer_path, prefix=".update-") as tmp:
                new_dir = Path(tmp) / path.name
                self._storage_provider.clone_and_checkout(path.name, new_dir, branch=branch)
                if not (new_dir / "description.xml").exists():
                    return self._report_error(
                        table, path, _STORAGE_PROVIDER_NAME, "Downloaded archive has no description.xml"
                    )

                new_description = new_dir / "description.json"
                new_build = Product.from_json_file(new_description).build if new_description.exists() else None
                new_commit = new_build.commit if new_build else ""

                # Reached when no description is published next to the archive.
                if new_commit and new_commit == old_commit:
                    return self._report_up_to_date(table, path, branch, old_commit)

                shutil.rmtree(path)
                new_dir.rename(path)
        except (ProviderError, ValueError, OSError) as e:
            return self._report_error(table, path, _STORAGE_PROVIDER_NAME, str(e))

        table.complete_installation(
            product_name=path.name,
            provider_name=_STORAGE_PROVIDER_NAME,
            status="success",
            details=f"{branch} {old_commit[:10]} → {new_commit[:10]}",
        )
        return True

    @staticmethod
    def _report_up_to_date(table: InstallationTable, path: Path, branch: str, commit: str) -> bool:
        """Record a storage download already at the latest commit of its branch.

        Args:
            table: Table the outcome is reported to.
            path: Product folder.
            branch: Build branch of the product.
            commit: Installed commit.

        Returns:
            Always True, so callers can return it directly.

        """
        table.complete_installation(
            product_name=path.name,
            provider_name=_STORAGE_PROVIDER_NAME,
            status="skipped",
            details=f"{branch} already at {commit[:10]}",
        )
        return True

    def _update_bundle(self, table: InstallationTable) -> None:
        """Install the latest bundle sharing the name and ``major.minor`` of the cached one.

        Args:
            table: Table the bundle products are reported to.

        """
        current = Bundle.from_json((self.installer_path / LOCAL_BUNDLE_FILE_NAME).read_text(encoding="utf-8"))
        latest = find_latest_bundle_name(
            build_configured_storage(self.storage_backend.value, area="bundles"), current.name, current.version
        )
        log.info("Updating bundle %s %s to %s", current.name, current.version.to_json_str(), latest)
        BundleDownloadable(
            storage_name=self.storage_backend,
            name=latest,
            installer_dir=self.installer_path,
            table=table,
        ).download(self.installer_path)

    @staticmethod
    def _report_error(table: InstallationTable, path: Path, provider_name: str, message: str) -> bool:
        """Record a failed product update.

        Args:
            table: Table the error is reported to.
            path: Folder of the product that failed.
            provider_name: Provider column of the row.
            message: Error shown in the table.

        Returns:
            Always False, so callers can return it directly.

        """
        log.debug("Failed to update '%s': %s", path, message)
        table.complete_installation(
            product_name=path.name,
            provider_name=provider_name,
            status="error",
            error_message=message,
        )
        return False
