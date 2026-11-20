"""Shared PostgreSQL helpers for schema application and versioning."""

import base64
import hashlib
import hmac
import os
import secrets
import subprocess
from pathlib import Path

import click
import psycopg

from database.base import DbSettings
from utils.Logger import logger

SCHEMA_VERSION_TABLE = "__schema_version"

# Default database password used when neither an explicit password nor a
# random one is requested.
DEFAULT_DB_PASSWORD = "kbot_db_pwd"  # noqa: S105

# Salt size used by kbot's 'utils.SafeEncrypt' (AES.block_size).
SAFE_ENCRYPT_SALT_SIZE = 16

log = logger.get_package_logger("database")


def resolve_db_password(db_password: str | None, *, no_password: bool) -> tuple[str, str | None]:
    """Resolve the database password to use, generating one if requested.

    Args:
        db_password: Password explicitly provided by the caller, if any.
        no_password: Whether a random password should be generated when
            ``db_password`` is not set.

    Returns:
        A tuple of ``(password, generated_password)``, where ``generated_password``
        is set only when a random password was generated (so it can be shown
        to the user).

    """
    if db_password:
        return db_password, None
    if no_password:
        generated = secrets.token_urlsafe(16)
        return generated, generated
    return DEFAULT_DB_PASSWORD, None


def resolve_admin_password(*, no_password: bool) -> tuple[str, str | None]:
    """Resolve the kbot admin password from 'KBOT_ADMIN_PASSWORD', or generate one.

    Unlike `resolve_db_password`, there is no silent default: the admin
    password must either be provided via the environment variable or
    explicitly generated with `no_password`.

    Args:
        no_password: Whether a random password should be generated when
            'KBOT_ADMIN_PASSWORD' is not set.

    Returns:
        A tuple of ``(password, generated_password)``, where ``generated_password``
        is set only when a random password was generated (so it can be shown
        to the user).

    Raises:
        click.UsageError: If 'KBOT_ADMIN_PASSWORD' is not set and `no_password`
            is False.

    """
    env_password = os.environ.get("KBOT_ADMIN_PASSWORD")
    if env_password:
        return env_password, None
    if no_password:
        generated = secrets.token_urlsafe(16)
        return generated, generated
    msg = "Admin password required: set 'KBOT_ADMIN_PASSWORD' or use '--no-admin-password'."
    raise click.UsageError(msg)


def connect(settings: DbSettings, *, database: str | None = None) -> psycopg.Connection:
    """Open a psycopg connection using the given settings.

    Args:
        settings: Connection settings (host, port, credentials).
        database: Database name to connect to. If None, uses ``settings.database``.

    Returns:
        An open psycopg connection.

    """
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=database or settings.database,
        user=settings.user,
        password=settings.password,
    )


def safe_encrypt(password: str, stored_password: str | None = None) -> str:
    """Hash a kbot user password the way kbot stores it in 'users_im_account.pwd'.

    Reimplements kbot's 'utils.SafeEncrypt' (which can't be imported here):
    ``base64(hex(HMAC-SHA256(salt, password)) + b"$" + salt)``, with a random
    16-byte salt. kbot checks a password with
    ``stored == SafeEncrypt(password, stored)``, reusing the stored salt.

    Args:
        password: Clear-text password.
        stored_password: A previously hashed password whose salt should be
            reused, or None to generate a new salt.

    Returns:
        The hashed password, as stored in the database.

    """
    if stored_password is None:
        salt = secrets.token_bytes(SAFE_ENCRYPT_SALT_SIZE)
    else:
        salt = base64.b64decode(stored_password)[-SAFE_ENCRYPT_SALT_SIZE:]
    digest = hmac.new(salt, password.encode("utf-8"), hashlib.sha256).hexdigest()
    return base64.b64encode(digest.encode("utf-8") + b"$" + salt).decode("utf-8")


def set_admin_password(settings: DbSettings, password: str) -> None:
    """Set the kbot admin user's password in the database.

    Mirrors the legacy 'setup_workarea._LoadAndLearn' admin-password update:
    the password is hashed with `safe_encrypt` (like the legacy
    'utils.SafeEncrypt') and stored using a parameterized query instead of
    being interpolated into SQL.

    Args:
        settings: Connection settings.
        password: New clear-text password for the kbot 'admin' user.

    Raises:
        RuntimeError: If there is no 'admin' account to update.

    """
    query = "UPDATE users_im_account SET pwd = %s WHERE user_id = (SELECT user_id FROM users WHERE user_name = 'admin')"
    with connect(settings) as conn, conn.cursor() as cur:
        cur.execute(query, (safe_encrypt(password),))
        if not cur.rowcount:
            # 'Load.py' only logs a failing step: without this check, a failed users load goes unnoticed
            msg = "No 'admin' account found in the database: the users load (users.conf) did not create it."
            raise RuntimeError(msg)
        conn.commit()


def drop_owned_objects(settings: DbSettings) -> None:
    """Drop every object (tables, views, sequences...) owned by the connected user.

    Mirrors the legacy 'uninstall.sh' erasure of an external database.

    Args:
        settings: Connection settings.

    """
    with connect(settings) as conn, conn.cursor() as cur:
        cur.execute("DROP OWNED BY CURRENT_USER")
        conn.commit()


class DatabaseDumpError(RuntimeError):
    """Raised when dumping the database via `pg_dump` fails."""


def dump_database(settings: DbSettings, path: Path) -> None:
    """Dump the database's 'public' schema into a plain SQL file.

    Mirrors the legacy 'dump_db.sh', using the `pg_dump` binary next to
    ``settings.psql_path``. The dump can be restored with `psql -f`.

    Args:
        settings: Connection settings.
        path: SQL file to write; its parent directory is created if needed.

    Raises:
        DatabaseDumpError: If `pg_dump` fails.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(settings.psql_path.with_name("pg_dump")),
        "-h",
        settings.host,
        "-p",
        str(settings.port),
        "-U",
        settings.user,
        "--no-privileges",
        "--no-owner",
        "-n",
        "public",
        "-f",
        str(path),
        settings.database,
    ]
    env = {**os.environ, "PGPASSWORD": settings.password}

    result = subprocess.run(  # noqa: S603
        command,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode:
        msg = f"Failed to dump database '{settings.database}' to {path}: {result.stderr.strip()}"
        raise DatabaseDumpError(msg)


class SqlFileError(RuntimeError):
    """Raised when applying a SQL file via `psql` fails."""


def execute_sql_file(settings: DbSettings, path: Path) -> None:
    r"""Apply a SQL file against the database using the `psql` client.

    Schema and upgrade files are shipped as `psql` scripts, not plain SQL:
    they may use client-side meta-commands (e.g. `\\set schema_version 192`
    followed by `:schema_version`), which a pure SQL connector like psycopg
    cannot parse. Shelling out to the real `psql` binary mirrors the legacy
    installer's behavior and supports this syntax natively.

    Args:
        settings: Connection settings, including the `psql` binary to use.
        path: Path to the SQL file to execute.

    Raises:
        SqlFileError: If `psql` exits with a non-zero status.

    """
    command = [
        str(settings.psql_path),
        "-v",
        "ON_ERROR_STOP=1",
        "-q",
        "-h",
        settings.host,
        "-p",
        str(settings.port),
        "-U",
        settings.user,
        "-d",
        settings.database,
        "-f",
        str(path),
    ]
    env = {**os.environ, "PGPASSWORD": settings.password}

    result = subprocess.run(  # noqa: S603
        command,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode:
        msg = f"Failed to apply SQL file {path}: {result.stderr.strip()}"
        raise SqlFileError(msg)


def ensure_version_table(settings: DbSettings) -> None:
    """Create the schema version tracking table if it does not exist.

    Args:
        settings: Connection settings.

    """
    with connect(settings) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
                CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """
        )


def get_applied_version(settings: DbSettings) -> set[str]:
    """Return the set of schema versions already applied to the database.

    Args:
        settings: Connection settings.

    Returns:
        The set of applied version identifiers.

    """
    ensure_version_table(settings)

    with connect(settings) as conn, conn.cursor() as cur:
        # SCHEMA_VERSION_TABLE is a hardcoded module constant, not user input.
        cur.execute(f"SELECT version from {SCHEMA_VERSION_TABLE}")  # noqa: S608
        return {row[0] for row in cur.fetchall()}


def mark_version_applied(settings: DbSettings, version: str) -> None:
    """Record a schema version as applied in the version table.

    Args:
        settings: Connection settings.
        version: Version identifier to record.

    """
    with connect(settings) as conn, conn.cursor() as cur:
        # SCHEMA_VERSION_TABLE is a hardcoded module constant, not user input.
        insert_sql = f"""
                    INSERT INTO {SCHEMA_VERSION_TABLE} (version)
                    VALUES (%s)
                    ON CONFLICT DO NOTHING
                """  # noqa: S608
        cur.execute(insert_sql, (version,))


def is_database_empty(settings: DbSettings) -> bool:
    """Check whether the database has no tables in the public schema.

    Args:
        settings: Connection settings.

    Returns:
        True if the database has no tables, False otherwise.

    """
    with connect(settings) as conn, conn.cursor() as cur:
        cur.execute(
            """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
        )
        row = cur.fetchone()
        return row is not None and not row[0]


def apply_schema(settings: DbSettings) -> None:
    """Apply every product schema file and record the target version if set.

    ``settings.schema_paths`` is expected to be ordered dependencies-first, so
    that a top level product's schema (which may reference tables defined by
    its dependencies) is applied last. Some products (e.g. customer products)
    do not ship their own ``db/init/db_schema.sql``, relying instead on a
    dependency's schema; missing files are skipped rather than treated as an
    error.

    Args:
        settings: Connection and schema settings.

    """
    applied_any = False

    for schema_path in settings.schema_paths:
        if not schema_path.is_file():
            log.info(
                "No schema file found at %s, skipping schema initialization.",
                schema_path,
            )
            continue

        execute_sql_file(settings=settings, path=schema_path)
        applied_any = True

    if not applied_any:
        return

    ensure_version_table(settings=settings)

    if settings.target_version:
        mark_version_applied(settings=settings, version=settings.target_version)


def upgrade_files(settings: DbSettings) -> list[Path]:
    """List available upgrade SQL files in application order.

    Args:
        settings: Connection and schema settings.

    Returns:
        Sorted paths of upgrade files, or an empty list if no upgrades directory
        is configured.

    """
    if settings.upgrades_dir is None:
        return []

    return sorted(settings.upgrades_dir.glob("upgrade_*.sql"))


def version_from_upgrade_file(path: Path) -> str:
    """Extract the version identifier from an upgrade file name.

    Args:
        path: Path to an upgrade SQL file, named ``upgrade_{version}.sql``.

    Returns:
        The version identifier encoded in the file name.

    """
    return path.stem.removeprefix("upgrade_")


def apply_missing_upgrades(settings: DbSettings) -> None:
    """Apply all upgrade files whose version has not yet been recorded.

    Args:
        settings: Connection and schema settings.

    """
    applied = get_applied_version(settings=settings)

    for path in upgrade_files(settings=settings):
        version = version_from_upgrade_file(path=path)

        if version in applied:
            continue

        execute_sql_file(settings=settings, path=path)
        mark_version_applied(settings=settings, version=version)
