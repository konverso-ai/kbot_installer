"""WorkareaInstallable class for managing workarea installations."""

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from utils.Logger import logger
from utils.product.product import Product
from utils.version import Version
from workarea.utils import (
    apply_rules,
    cleanup_unused_tests_dir,
    clear_workarea,
    runtime_variables,
    setup_drf_spectacular_static,
    setup_drf_yasg_static,
    setup_kbot_conf,
    setup_products,
    setup_products_registry,
    setup_runtime_dirs,
)
from workarea.workarea import Workarea

log = logger.get_package_logger("installable")

# From this kbot version on, kbot discovers its products from `var/products.json`
# instead of the workarea's `products/` symlinks, no longer reads `conf/`, and
# serves the drf-spectacular static assets instead of the drf-yasg ones.
KBOT_2026_01 = Version("2026.01")


class WorkareaInstallable(BaseModel):
    """Installable that lays out and maintains a whole workarea on disk.

    Unlike `ProductInstallable`/`BundleInstallable`, this installable does not
    represent a single downloadable unit: it applies workarea rules for every
    product already present under `workarea.installer_root`. The layout
    depends on the installed kbot version (see `kbot_version`). Updating or
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

        Creates the work root and the product layout kbot discovers its
        products from, applies workarea rules for every existing product, then
        sets up the runtime directories and static assets, and removes unused
        test directories. From kbot 2026.01 on, products are listed in
        `var/products.json` and the static assets come from drf-spectacular;
        before, products are symlinked under `products/` next to a default
        `conf/kbot.conf`, and the static assets come from drf-yasg.

        The product layout is written first: it is what marks the directory as
        a kbot workarea for `uninstall`, so a layout failing midway still
        leaves a workarea that can be uninstalled. Outdated copies laid out by
        `refresh` rules are rewritten (after confirmation in update mode).
        """
        self.workarea.work_root.mkdir(parents=True, exist_ok=True)

        variables = runtime_variables(self.workarea.work_root)
        product_roots = list(self._iter_product_roots())
        uses_products_registry = self.kbot_version() >= KBOT_2026_01

        if uses_products_registry:
            setup_products_registry(self.workarea.work_root, product_roots)
        else:
            setup_products(self.workarea.work_root, product_roots)

        claimed: set[Path] = set()
        for product_root in product_roots:
            apply_rules(
                product_root=product_root,
                work_root=self.workarea.work_root,
                rules=self.workarea.rules,
                runtime_variables=variables,
                claimed=claimed,
                interactive=self.update_mode,
            )

        setup_runtime_dirs(self.workarea.work_root)
        if uses_products_registry:
            setup_drf_spectacular_static(self.workarea.work_root, self.workarea.installer_root)
        else:
            setup_kbot_conf(self.workarea.work_root)
            setup_drf_yasg_static(self.workarea.work_root, self.workarea.installer_root)
        cleanup_unused_tests_dir(
            self.workarea.work_root,
            product_roots,
            interactive=self.update_mode,
        )

    def kbot_version(self) -> Version:
        """Read the version of the kbot product installed under the installer root.

        Returns:
            The version declared in `kbot/description.xml`, or an empty version
            (older than any release, hence the legacy layout) if kbot is not
            installed.

        """
        description_xml = self.workarea.installer_root / "kbot" / "description.xml"
        if not description_xml.exists():
            return Version.empty()
        return Product.from_xml_file(description_xml).version

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
