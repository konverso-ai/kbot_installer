"""Install each downloaded product's Python requirements into 3rdparty Python."""

import subprocess
from pathlib import Path

from installer_support.installer_service import InstallerService
from utils.Logger import logger

log = logger.get_package_logger("installer_support")

# Product types whose root ``requirements.txt`` must be installed into the
# 3rdparty Python (mirrors the legacy ``setup_workarea._UpdatePythonPackages``).
_PYTHON_REQUIREMENTS_PRODUCT_TYPES = frozenset({"solution", "customer"})


def install_product_python_requirements(installer_path: Path) -> None:
    """Install each solution/customer product's ``requirements.txt`` into 3rdparty Python.

    Reuses the downloaded ``kbot/bin/pip3.sh`` wrapper, which sources
    ``kbot/bin/env.sh`` and handles the 3rdparty Python relocation
    (``_sysconfigdata`` placeholder) before running ``pip``. This runs after
    the product tree has been downloaded, so the wrapper exists and is
    consistent; the installer never depends on a kbot script *before* download.

    Args:
        installer_path: Installer directory holding the downloaded products.

    Raises:
        RuntimeError: If installing a product's requirements fails.

    """
    pip3 = installer_path / "kbot" / "bin" / "pip3.sh"
    if not pip3.is_file():
        log.warning("Skipping product Python requirements: '%s' not found.", pip3)
        return

    service = InstallerService(installer_path)
    for product in service.load_products_from_disk():
        if product.type not in _PYTHON_REQUIREMENTS_PRODUCT_TYPES:
            continue
        req_path = installer_path / product.name / "requirements.txt"
        if not req_path.is_file():
            continue

        log.info("Installing Python requirements for '%s' into 3rdparty Python...", product.name)
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
            msg = f"Failed to install Python requirements for '{product.name}' (exit {result.returncode})."
            raise RuntimeError(msg)
