"""Shared PostgreSQL helpers for schema application and versioning."""

from pathlib import Path

import psycopg

from database.base import DbSettings

SCHEMA_VERSION_TABLE = "__schema_version"


def connect(
    settings: DbSettings, *, database: str | None = None
) -> psycopg.Connection:
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


def execute_sql_file(settings: DbSettings, path: Path) -> None:
    """Read and execute a SQL file against the database.

    Args:
        settings: Connection settings.
        path: Path to the SQL file to execute.

    """
    sql = path.read_text(encoding="utf-8")

    with connect(settings) as conn, conn.cursor() as cur:
        # SQL comes from a trusted schema file; pass it as bytes since the
        # execute overloads only accept LiteralString, not a runtime str.
        cur.execute(sql.encode("utf-8"))


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
        return row is not None and row[0] == 0


def apply_schema(settings: DbSettings) -> None:
    """Apply the initial schema file and record the target version if set.

    Args:
        settings: Connection and schema settings.

    """
    execute_sql_file(settings=settings, path=settings.schema_path)
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
