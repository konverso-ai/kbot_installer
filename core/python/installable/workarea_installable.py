"""WorkareaInstallable class for managing workarea installations."""

import getpass
import logging
import os
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field
from typing_extensions import override

from installable.base import InstallableBase
from installable.product_collection import ProductCollection
from installable.updater.factory import UpdaterName, add_updater
from workarea.utils import (
    apply_rules,
    cleanup_unused_tests_dir,
    is_broken_symlink,
    setup_drf_yasg_static,
    setup_kbot_conf,
    setup_products,
    setup_runtime_dirs,
)
from workarea.workarea import Workarea

logger = logging.getLogger(__name__)


class WorkareaInstallable(BaseModel, InstallableBase):
    """Installable that lays out and maintains a whole workarea on disk.

    Unlike `ProductInstallable`/`BundleInstallable`, this installable does not
    represent a single downloadable unit: it applies workarea rules for every
    product already present under `workarea.installer_root` and delegates
    updates to the configured updater strategy (see `installable.updater`).

    Attributes:
        workarea: The `Workarea` model describing installer root, work root, products, and rules.
        update_mode: Updater strategy used by `update`.
        runtime_pythonpath: Paths (relative to `work_root`) exposed on `PYTHONPATH` at runtime.

    """

    workarea: Workarea

    update_mode: Annotated[UpdaterName, Field(default=UpdaterName.SMOOTH)]

    runtime_pythonpath: Annotated[
        list[Path],
        Field(
            default_factory=lambda: [
                Path("core/python"),
                Path("rest"),
            ],
        ),
    ]

    @override
    def install(self) -> None:
        """Build the workarea from scratch.

        Creates the work root, applies workarea rules for every existing
        product, then sets up the kbot configuration, runtime directories,
        product registry, and static assets, and removes unused test
        directories.
        """
        self.workarea.work_root.mkdir(parents=True, exist_ok=True)

        runtime_variables = self._runtime_variables()

        for product_root in self._iter_product_roots():
            apply_rules(
                product_root=product_root,
                work_root=self.workarea.work_root,
                rules=self.workarea.rules,
                runtime_variables=runtime_variables,
            )

        setup_kbot_conf(self.workarea.work_root)
        setup_runtime_dirs(self.workarea.work_root)
        setup_products(self.workarea.work_root, self.workarea.products)
        setup_drf_yasg_static(self.workarea.work_root)
        cleanup_unused_tests_dir(
            self.workarea.work_root,
            self.workarea.products,
            interactive=self.update_mode == UpdaterName.INTERACTIVE,
        )

    @override
    def update(self) -> None:
        """Update the workarea using the configured updater strategy.

        Resolves the updater named by `update_mode` (see `installable.updater.factory`)
        and runs it against this workarea.
        """
        updater = add_updater(name=self.update_mode.value, workarea=self)
        updater()

    @override
    def repair(self) -> None:
        """Repair the workarea using the `repair` updater strategy, regardless of `update_mode`."""
        updater = add_updater(name=UpdaterName.REPAIR.value, workarea=self)
        updater()

    def clear(self) -> None:
        """Remove every file, symlink, and directory directly under the work root."""
        for child in self.workarea.work_root.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            else:
                shutil.rmtree(child)

    def repair_broken_links(self, *, interactive: bool = False) -> None:
        """Find and remove broken symlinks under the work root.

        Args:
            interactive: If True, prompt for confirmation before removing each broken
                symlink; otherwise remove them all without asking.

        """
        for path in self.workarea.work_root.rglob("*"):
            if not is_broken_symlink(path=path):
                continue

            if interactive:
                answer: str = input(f"Broken symlink {path}. Rebuild it? [y/N] ")
                if answer.lower() not in {"y", "yes"}:
                    continue

            path.unlink()

    def _iter_product_roots(self) -> Iterable[Path]:
        for product in self.workarea.products:
            product_root = self.workarea.installer_root / product
            if product_root.exists():
                yield product_root

    def _runtime_variables(self) -> dict[str, str]:
        return {
            "__KBOT_HOME__": str(self.workarea.work_root.resolve()),
            "__KBOT_USER__": getpass.getuser(),
        }

    def pythonpath(self) -> str:
        """Build the runtime `PYTHONPATH` value for this workarea.

        Returns:
            `os.pathsep`-joined, resolved absolute paths for each entry in
            `runtime_pythonpath`, rooted at `workarea.work_root`.

        """
        return os.pathsep.join(
            str((self.workarea.work_root / path).resolve())
            for path in self.runtime_pythonpath
        )

    def runtime_env(self) -> dict[str, str]:
        """Build the environment to run kbot processes against this workarea.

        Returns:
            A copy of the current process environment with `PYTHONPATH` set to
            `pythonpath()`.

        Raises:
            FileNotFoundError: If a `runtime_pythonpath` entry is missing under `work_root`.

        """
        self._assert_runtime_ready()
        env = os.environ.copy()
        env["PYTHONPATH"] = self.pythonpath()
        return env

    def _assert_runtime_ready(self) -> None:
        for path in self.runtime_pythonpath:
            full_path = self.workarea.work_root / path
            if not full_path.exists():
                msg = f"Missing runtime PYTHONPATH entry: {full_path}"
                raise FileNotFoundError(msg)

    @override
    def load_from_installer_folder(self, folder_path: Path) -> None:
        """Not supported for a workarea.

        Raises:
            NotImplementedError: Always; a workarea is not loaded from a single installer folder.

        """
        msg = "load_from_installer_folder is not implemented for WorkareaInstallable"
        raise NotImplementedError(msg)

    @override
    def to_xml(self) -> str:
        """Not supported for a workarea.

        Raises:
            NotImplementedError: Always; a workarea has no XML description.

        """
        msg = "to_xml is not implemented for WorkareaInstallable"
        raise NotImplementedError(msg)

    @override
    def to_json(self) -> dict[str, Any]:
        """Not supported for a workarea.

        Raises:
            NotImplementedError: Always; a workarea has no JSON description.

        """
        msg = "to_json is not implemented for WorkareaInstallable"
        raise NotImplementedError(msg)

    @override
    def download(self, path: Path, *, dependencies: bool = True) -> None:
        """Not supported for a workarea.

        Raises:
            NotImplementedError: Always; a workarea is assembled from already-downloaded products,
                not downloaded itself.

        """
        msg = "download is not implemented for WorkareaInstallable"
        raise NotImplementedError(msg)

    @override
    def get_dependencies(self) -> ProductCollection:
        """Not supported for a workarea.

        Raises:
            NotImplementedError: Always; a workarea aggregates a fixed product list rather
                than resolving dependencies of its own.

        """
        msg = "get_dependencies is not implemented for WorkareaInstallable"
        raise NotImplementedError(msg)
