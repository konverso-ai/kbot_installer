"""Run workarea 'bin/' scripts ('kbot.sh' subcommands, DB upgrade scripts), the IAM-only load and the license check."""

import subprocess
from pathlib import Path

from utils.Logger import logger

log = logger.get_package_logger("installer_support")


def run_workarea_script(workarea_path: Path, script: str, *args: str) -> None:
    """Run a script of the workarea's 'bin/' directory.

    The workarea scripts source their own 'env.sh', which sets up the runtime
    environment (database, paths) before doing their work.

    Args:
        workarea_path: Workarea directory holding 'bin/<script>'.
        script: Script file name (e.g. 'upgrade_db.sh').
        *args: Arguments passed to the script.

    Raises:
        RuntimeError: If the script exits with a non-zero status.

    """
    cmd = [str(workarea_path / "bin" / script), *args]
    log.info("Running '%s'...", " ".join(cmd))
    result = subprocess.run(cmd, check=False)  # noqa: S603
    if result.returncode:
        msg = f"'{' '.join(cmd)}' failed (exit {result.returncode})."
        raise RuntimeError(msg)


def run_kbot_command(workarea_path: Path, command: str) -> None:
    """Run a 'kbot.sh' subcommand against a workarea.

    Reuses the installed workarea's own 'bin/kbot.sh' wrapper, which sources its
    'env.sh' and sets up the runtime environment before running the subcommand
    (mirrors the legacy 'setup_workarea._LoadAndLearn', which shelled out to the
    same script for its 'load' and 'learn' steps).

    Args:
        workarea_path: Workarea directory holding 'bin/kbot.sh'.
        command: Subcommand to run (e.g. 'load', 'learn').

    Raises:
        RuntimeError: If the command exits with a non-zero status.

    """
    run_workarea_script(workarea_path, "kbot.sh", command)


def validate_license(workarea_path: Path) -> None:
    """Validate the workarea's 'var/license.key' with kbot's own license checker.

    Runs 'bin/python.sh -m utils.License <work>/var/license.key': kbot's
    'utils.License' module checks the host, end date and signed key of the
    license the workarea rules link from the products' 'conf/license.key', so
    an invalid license fails the install instead of the first kbot start
    (mirrors the legacy 'setup_workarea._ValidateLicense').

    Args:
        workarea_path: Workarea directory holding 'bin/python.sh'.

    Raises:
        RuntimeError: If the license is missing or invalid.

    """
    python_sh = workarea_path / "bin" / "python.sh"
    license_key = workarea_path / "var" / "license.key"
    log.info("Validating license '%s'...", license_key)
    result = subprocess.run(  # noqa: S603
        [str(python_sh), "-m", "utils.License", str(license_key)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stdout + result.stderr).strip()
        msg = f"Invalid license '{license_key}': {detail}"
        raise RuntimeError(msg)


def run_kbot_iam_load(workarea_path: Path) -> None:
    """Load only the identity and access management data (permissions, roles, users).

    Runs 'bin/core.sh load -p': unlike 'kbot.sh load', 'core.sh' forwards its
    arguments to 'Load.py', whose '-p/--profiles' option restricts the load to
    the IAM step. This creates the 'users.conf' accounts (including 'admin' and
    its 'Administrator' role) without loading the rest of the data.

    Args:
        workarea_path: Workarea directory holding 'bin/core.sh'.

    Raises:
        RuntimeError: If the command exits with a non-zero status.

    """
    run_workarea_script(workarea_path, "core.sh", "load", "-p")
