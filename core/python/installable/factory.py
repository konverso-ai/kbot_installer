"""Factory functions for installable instances."""

from pathlib import Path
from typing import Literal, cast

from installable.workarea_installable import WorkareaInstallable
from utils.factory.loader import factory_class
from workarea.rules_config import load_default_rules
from workarea.workarea import Workarea


def create_installable(
    installable_name: Literal["workarea"],
    **kwargs: object,
) -> WorkareaInstallable:
    """Create an installable instance by name.

    Naming convention:
    - Module: ``{name}_installable`` (e.g. ``workarea_installable``)
    - Class: ``{Name}Installable`` (e.g. ``WorkareaInstallable``)

    Args:
        installable_name: Installable type. Only ``workarea`` is supported.
        **kwargs: Keyword arguments passed to the class constructor.

    Returns:
        An instance of the requested installable class.

    """
    cls = factory_class(installable_name, "installable")
    return cast("WorkareaInstallable", cls(**kwargs))


def build_workarea(installer_path: Path, workarea_path: Path) -> WorkareaInstallable:
    """Build the WorkareaInstallable laying out the workarea from downloaded products.

    Args:
        installer_path: Installer directory holding the downloaded products.
        workarea_path: Workarea directory to build.

    Returns:
        A ``WorkareaInstallable`` ready to have ``.install()`` called.

    """
    # Local import: installer_support.installer_service imports
    # installable.dependency_graph/renderer, and installable/__init__.py
    # imports this factory module, so a module-level import here would create
    # an import cycle.
    from installer_support.installer_service import InstallerService  # noqa: PLC0415

    service = InstallerService(installer_path)
    products = [Path(product.name) for product in service.load_products_from_disk()]

    workarea = Workarea(
        installer_root=installer_path,
        work_root=workarea_path,
        products=products,
        rules=load_default_rules(),
    )
    return WorkareaInstallable(workarea=workarea)
