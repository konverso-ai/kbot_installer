"""Install each downloaded product's Python requirements into 3rdparty Python."""

import subprocess
from pathlib import Path

from installer_support.installer_service import InstallerService
from installer_support.thirdparty_env import resolve_site_packages_dir
from utils.Logger import logger

log = logger.get_package_logger("installer_support")

# Product types whose root ``requirements.txt`` must be installed into the
# 3rdparty Python: the legacy ``setup_workarea._UpdatePythonPackages`` types
# (solution, customer), plus framework since ``kbot_installer``'s modules are
# linked into the workarea and imported by kbot at runtime.
_PYTHON_REQUIREMENTS_PRODUCT_TYPES = frozenset({"framework", "solution", "customer"})


def install_product_python_requirements(installer_path: Path) -> None:
    """Install each framework/solution/customer product's ``requirements.txt`` into 3rdparty Python.

    Reuses the downloaded ``kbot/bin/pip3.sh`` wrapper, which sources
    ``kbot/bin/env.sh`` and handles the 3rdparty Python relocation
    (``_sysconfigdata`` placeholder) before running ``pip``. This runs after
    the product tree has been downloaded, so the wrapper exists and is
    consistent; the installer never depends on a kbot script *before* download.

    Args:
        installer_path: Installer directory holding the downloaded products.

    Raises:
        RuntimeError: If the 3rdparty Python is missing while requirements must
            be installed, or if installing a product's requirements fails.

    """
    pip3 = installer_path / "kbot" / "bin" / "pip3.sh"
    if not pip3.is_file():
        log.warning("Skipping product Python requirements: '%s' not found.", pip3)
        return

    requirements: list[tuple[str, Path]] = []
    for product in InstallerService(installer_path).load_products_from_disk():
        req_path = installer_path / product.name / "requirements.txt"
        if product.type in _PYTHON_REQUIREMENTS_PRODUCT_TYPES and req_path.is_file():
            requirements.append((product.name, req_path))
    if not requirements:
        return

    # pip3.sh takes the interpreter from 3rdparty/versions.env: without it, it
    # would run '/bin/python' and rewrite '/lib/python/_sysconfigdata...'.
    site_packages = resolve_site_packages_dir(installer_path)
    if site_packages is None or not site_packages.is_dir():
        msg = (
            f"Cannot install Python requirements: the 3rdparty Python is missing from '{installer_path}' "
            f"('3rdparty/versions.env' or its Python directory not found)."
        )
        raise RuntimeError(msg)

    for name, req_path in requirements:
        log.info("Installing Python requirements for '%s' into 3rdparty Python...", name)
        result = subprocess.run(  # noqa: S603
            [
                str(pip3),
                "install",
                "-r",
                str(req_path),
                "--quiet",
                "--disable-pip-version-check",
            ],
            check=False,
        )
        if result.returncode:
            msg = f"Failed to install Python requirements for '{name}' (exit {result.returncode})."
            raise RuntimeError(msg)
