"""PostgreSQL cluster process management (initdb/pg_ctl).

This module owns the OS-process side of running a local, internal PostgreSQL
server: creating the data directory and starting/stopping the server binary.
It is kept separate from `database.internal_db`, which only ever talks SQL
over a live connection via psycopg2.
"""

import subprocess

from database.base import InternalDbSettings
from utils.Logger import logger

log = logger.get_package_logger("database")


class PostgresClusterError(RuntimeError):
    """Raised when a PostgreSQL cluster operation fails."""


def is_initialized(settings: InternalDbSettings) -> bool:
    """Check whether the PostgreSQL data directory has already been created.

    Args:
        settings: Internal database settings, providing the data directory.

    Returns:
        True if the cluster has already been initialized via `initdb`.

    """
    return (settings.pg_data / "PG_VERSION").exists()


def initdb(settings: InternalDbSettings) -> None:
    """Create the PostgreSQL data directory for a new cluster.

    Args:
        settings: Internal database settings, providing the data directory,
            encoding, and locale to initialize the cluster with.

    Raises:
        PostgresClusterError: If `initdb` (invoked via `pg_ctl`) fails.

    """
    settings.pg_data.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(  # noqa: S603
        [
            str(settings.pg_bin / "pg_ctl"),
            "-D",
            str(settings.pg_data),
            "-o",
            f"-E {settings.encoding}",
            "-o",
            f"--locale={settings.locale}",
            "initdb",
        ],
        check=False,
        capture_output=True,
    )

    if result.returncode != 0:
        msg = f"initdb failed: {result.stderr.decode(errors='replace')}"
        raise PostgresClusterError(msg)


def is_running(settings: InternalDbSettings) -> bool:
    """Check whether the PostgreSQL server for this cluster is up.

    Args:
        settings: Internal database settings, providing the data directory.

    Returns:
        True if `pg_ctl status` reports the server as running.

    """
    result = subprocess.run(  # noqa: S603
        [
            str(settings.pg_bin / "pg_ctl"),
            "status",
            "--silent",
            "-D",
            str(settings.pg_data),
        ],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def start(settings: InternalDbSettings) -> None:
    """Start the PostgreSQL server for this cluster.

    Args:
        settings: Internal database settings, providing the data directory,
            log path, port, and optional Unix socket directory.

    Raises:
        PostgresClusterError: If the server does not report as running
            after the start attempt.

    """
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)

    options = ["-o", f"-p{settings.port}"]
    if settings.socket_dir is not None:
        settings.socket_dir.mkdir(parents=True, exist_ok=True)
        options += ["-o", f"-k{settings.socket_dir}"]

    subprocess.run(  # noqa: S603
        [
            str(settings.pg_bin / "pg_ctl"),
            "start",
            "-l",
            str(settings.log_path),
            "-D",
            str(settings.pg_data),
            "--silent",
            "-w",
            *options,
        ],
        check=False,
    )

    if not is_running(settings):
        msg = "PostgreSQL server failed to start."
        raise PostgresClusterError(msg)


def stop(settings: InternalDbSettings) -> None:
    """Stop the PostgreSQL server for this cluster.

    Args:
        settings: Internal database settings, providing the data directory.

    """
    subprocess.run(  # noqa: S603
        [
            str(settings.pg_bin / "pg_ctl"),
            "-D",
            str(settings.pg_data),
            "--silent",
            "stop",
        ],
        check=False,
    )


def ensure_running(settings: InternalDbSettings) -> None:
    """Initialize the cluster if needed, and make sure the server is running.

    Args:
        settings: Internal database settings.

    Raises:
        PostgresClusterError: If initialization or startup fails.

    """
    if not is_initialized(settings):
        log.info("Initializing PostgreSQL cluster at %s", settings.pg_data)
        initdb(settings)

    if not is_running(settings):
        log.info("Starting PostgreSQL server")
        start(settings)
