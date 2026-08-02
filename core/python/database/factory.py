"""Factory function for database backend instances.

Follows the project-wide naming convention: a ``mode`` resolves to the module
``{mode}_database`` and the class ``{Mode}Database`` (e.g. ``internal`` ->
``database.internal_database.InternalDatabase``). Each backend declares the
settings model it expects through its ``settings_cls`` attribute.
"""

from pathlib import Path
from typing import Literal, cast

from database.base import DatabaseBackend
from utils.factory.loader import factory_class

DbMode = Literal["internal", "external"]


def add_database(mode: DbMode, **kwargs) -> DatabaseBackend:
    """Create the database backend instance matching the given mode.

    Args:
        mode: Database mode, either ``"internal"`` or ``"external"``.
        **kwargs: Keyword arguments used to build the backend settings model.

    Returns:
        The database backend instance for the requested mode.

    Raises:
        ImportError: If no backend module exists for the given mode.
        AttributeError: If the backend class is not found in its module.

    """
    backend_cls = factory_class(name=mode, package="database")
    settings = backend_cls.settings_cls(**kwargs)
    return cast("DatabaseBackend", backend_cls(settings=settings))


def build_database(
    *,
    schema_paths: list[Path],
    db_host: str | None,
    db_port: int,
    db_user: str,
    password: str,
    db_name: str,
    workarea_path: Path,
    pg_dir: Path | None = None,
    admin_user: str = "postgres",
    admin_password: str = "postgres",  # noqa: S107
) -> DatabaseBackend:
    """Build, prepare and initialize the product database backend.

    Uses an externally managed database when ``db_host`` is set, otherwise
    bootstraps a local, installer-owned PostgreSQL cluster under the workarea.

    Args:
        schema_paths: Ordered list of ``db/init/db_schema.sql`` paths to apply, one per
            product involved in the installation (dependencies first, top level product last).
        db_host: External Postgres host, or None to use an internal cluster.
        db_port: Postgres port.
        db_user: Postgres application user.
        password: Postgres application password.
        db_name: Postgres database name.
        workarea_path: Workarea directory, used for the internal cluster's data/log paths.
        pg_dir: PostgreSQL installation directory, required when ``db_host`` is None.
        admin_user: Postgres admin user, used only for the internal cluster.
        admin_password: Postgres admin password, used only for the internal cluster.

    Returns:
        The prepared and initialized database backend instance.

    Raises:
        ValueError: If ``db_host`` is None and ``pg_dir`` was not provided.

    """
    if db_host:
        db = add_database(
            mode="external",
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=password,
            schema_paths=schema_paths,
            allow_schema_creation=True,
        )
    else:
        if pg_dir is None:
            msg = "'pg_dir' is required to build an internal database backend."
            raise ValueError(msg)

        db = add_database(
            mode="internal",
            host="localhost",
            port=db_port,
            database=db_name,
            user=db_user,
            password=password,
            schema_paths=schema_paths,
            pg_dir=pg_dir,
            pg_data=workarea_path / "var" / "db",
            log_path=workarea_path / "logs" / "postgres.log",
            admin_user=admin_user,
            admin_password=admin_password,
        )

    db.prepare()
    db.initialize()
    return db
