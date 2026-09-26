"""PostgreSQL cluster process management (initdb/pg_ctl).

This module owns the OS-process side of running a local, internal PostgreSQL
server: creating the data directory and starting/stopping the server binary.
It is kept separate from `database.internal_database`, which only ever talks SQL
over a live connection via psycopg.
"""

import socket
import subprocess
from pathlib import Path
from typing import cast

import psutil

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
            "-o",
            f"--username={settings.admin_user}",
            "initdb",
        ],
        check=False,
        capture_output=True,
    )

    if result.returncode:
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
    return not result.returncode


def _port_in_use(host: str, port: int) -> bool:
    """Check whether some process is already listening on `host`:`port`.

    Args:
        host: Host to probe.
        port: TCP port to probe.

    Returns:
        True if a TCP connection to `host`:`port` succeeds.

    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _find_port_owner_pid(port: int) -> int | None:
    """Best-effort lookup of the PID listening on `port`, for error messages.

    Args:
        port: TCP port to look up.

    Returns:
        The owning PID, or None if it cannot be determined (e.g. insufficient
        permissions, or no matching listening socket found).

    """
    try:
        connections = psutil.net_connections(kind="tcp")
    except (psutil.AccessDenied, PermissionError):
        return None

    for conn in connections:
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return cast("int | None", conn.pid)
    return None


def start(settings: InternalDbSettings) -> None:
    """Start the PostgreSQL server for this cluster.

    Args:
        settings: Internal database settings, providing the data directory,
            log path, port, and optional Unix socket directory.

    Raises:
        PostgresClusterError: If `settings.port` is already occupied by
            another process, or if the server does not report as running
            after the start attempt.

    """
    if _port_in_use(settings.host, settings.port):
        pid = _find_port_owner_pid(settings.port)
        owner = f" (in use by PID {pid}, possibly a leftover process from a previous run)" if pid else ""
        msg = f"Cannot start PostgreSQL: port {settings.port} on {settings.host} is already in use{owner}."
        raise PostgresClusterError(msg)

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
        msg = f"PostgreSQL server failed to start.\n{_tail_log(settings.log_path)}"
        raise PostgresClusterError(msg)


def _tail_log(log_path: Path, *, max_lines: int = 20) -> str:
    """Return the last lines of the PostgreSQL server log, for error reporting.

    Args:
        log_path: Path to the `pg_ctl`/`postgres` server log file.
        max_lines: Maximum number of trailing lines to return.

    Returns:
        The last `max_lines` lines of `log_path`, prefixed with a short
        header, or a note indicating the log file could not be read.

    """
    if not log_path.exists():
        return f"(no log file found at {log_path})"

    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"(could not read log file {log_path}: {exc})"

    tail = "\n".join(lines[-max_lines:])
    return f"--- last {min(len(lines), max_lines)} line(s) of {log_path} ---\n{tail}"


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
