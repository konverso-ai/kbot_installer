"""WorkareaInstallable class for managing workarea installations."""

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from utils.Logger import logger
from workarea.utils import (
    apply_rules,
    cleanup_unused_tests_dir,
    clear_workarea,
    runtime_variables,
    setup_drf_yasg_static,
    setup_kbot_conf,
    setup_products,
    setup_runtime_dirs,
)
from workarea.workarea import Workarea

log = logger.get_package_logger("installable")


class WorkareaInstallable(BaseModel):
    """Installable that lays out and maintains a whole workarea on disk.

    Unlike `ProductInstallable`/`BundleInstallable`, this installable does not
    represent a single downloadable unit: it applies workarea rules for every
    product already present under `workarea.installer_root`. Updating or
    repairing a workarea is done by instantiating `updatable.workarea_updatable.WorkareaUpdatable`
    directly with this installable's `workarea` and the desired strategy.

    Attributes:
        workarea: The `Workarea` model describing installer root, work root, products, and rules.
        update_mode: Whether `install` should remove unused test directories interactively.
        runtime_pythonpath: Paths (relative to `work_root`) exposed on `PYTHONPATH` at runtime.

    """

    workarea: Workarea

    update_mode: Annotated[bool, Field(default=False)]

    runtime_pythonpath: Annotated[
        list[Path],
        Field(
            default_factory=lambda: [
                Path("core/python"),
                Path("rest"),
            ],
        ),
    ]

    def install(self) -> None:
        """Build the workarea from scratch.

        Creates the work root, applies workarea rules for every existing
        product, then sets up the kbot configuration, runtime directories,
        product registry, and static assets, and removes unused test
        directories.
        """
        self.workarea.work_root.mkdir(parents=True, exist_ok=True)

        variables = runtime_variables(self.workarea.work_root)
        product_roots = list(self._iter_product_roots())

        for product_root in product_roots:
            apply_rules(
                product_root=product_root,
                work_root=self.workarea.work_root,
                rules=self.workarea.rules,
                runtime_variables=variables,
            )

        setup_kbot_conf(self.workarea.work_root)
        setup_runtime_dirs(self.workarea.work_root)
        setup_products(self.workarea.work_root, product_roots)
        setup_drf_yasg_static(self.workarea.work_root)
        cleanup_unused_tests_dir(
            self.workarea.work_root,
            product_roots,
            interactive=self.update_mode,
        )

    def clear(self) -> None:
        """Remove every file, symlink, and directory directly under the work root."""
        clear_workarea(self.workarea.work_root)

    def _iter_product_roots(self) -> Iterable[Path]:
        for product in self.workarea.products:
            product_root = self.workarea.installer_root / product
            if product_root.exists():
                yield product_root

    def pythonpath(self) -> str:
        """Build the runtime `PYTHONPATH` value for this workarea.

        Returns:
            `os.pathsep`-joined, resolved absolute paths for each entry in
            `runtime_pythonpath`, rooted at `workarea.work_root`.

        """
        return os.pathsep.join(str((self.workarea.work_root / path).resolve()) for path in self.runtime_pythonpath)

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
