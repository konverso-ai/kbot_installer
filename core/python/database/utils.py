from pathlib import Path

import psycopg2

from database.base import DbSettings

SCHEMA_VERSION_TABLE = "__schema_version"


def connect(settings: DbSettings, *, database: str | None = None):
    return psycopg2.connect(
        host=settings.host,
        port=settings.port,
        dbname=database or settings.database,
        user=settings.user,
        password=settings.password,
    )


def execute_sql_file(settings: DbSettings, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def ensure_version_table(settings: DbSettings) -> None:
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS {SCHEMA_VERSION_TABLE} (
                        version TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                """
            )


def get_applied_version(settings: DbSettings) -> set[str]:
    ensure_version_table(settings)

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT version from {SCHEMA_VERSION_TABLE}")
            return {row[0] for row in cur.fetchall()}


def mark_version_applied(settings: DbSettings, version: str) -> None:
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                    INSERT INTO {SCHEMA_VERSION_TABLE} (version)
                    VALUES (%s)
                    ON CONFLICT DO NOTHING
                """,
                (version,),
            )


def is_database_empty(settings: DbSettings) -> bool:
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
            )
            return cur.fetchone()[0] == 0


def apply_schema(settings: DbSettings) -> None:
    execute_sql_file(settings=settings, path=settings.schema_path)
    ensure_version_table(settings=settings)

    if settings.target_version:
        mark_version_applied(settings=settings, version=settings.target_version)


def upgrade_files(settings: DbSettings) -> list[Path]:
    if settings.upgrades_dir is None:
        return []

    return sorted(settings.upgrades_dir.glob("upgrade_*.sql"))


def version_from_upgrade_file(path: Path) -> str:
    return path.stem.removeprefix("upgrade_")


def apply_missing_upgrades(settings: DbSettings) -> None:
    applied = get_applied_version(settings=settings)

    for path in upgrade_files(settings=settings):
        version = version_from_upgrade_file(path=path)

        if version in applied:
            continue

        execute_sql_file(settings=settings, path=path)
        mark_version_applied(settings=settings, version=version)
