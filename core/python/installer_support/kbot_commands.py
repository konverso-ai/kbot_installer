"""Run 'kbot.sh' subcommands (load, learn) and the IAM-only load against an installed workarea."""

import subprocess
from pathlib import Path

from utils.Logger import logger

log = logger.get_package_logger("installer_support")


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
    kbot_sh = workarea_path / "bin" / "kbot.sh"
    log.info("Running '%s %s'...", kbot_sh, command)
    result = subprocess.run([str(kbot_sh), command], check=False)  # noqa: S603
    if result.returncode:
        msg = f"'{kbot_sh} {command}' failed (exit {result.returncode})."
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
    core_sh = workarea_path / "bin" / "core.sh"
    log.info("Running '%s load -p'...", core_sh)
    result = subprocess.run([str(core_sh), "load", "-p"], check=False)  # noqa: S603
    if result.returncode:
        msg = f"'{core_sh} load -p' failed (exit {result.returncode})."
        raise RuntimeError(msg)
