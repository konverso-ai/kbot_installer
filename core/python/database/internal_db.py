"""Internal PostgreSQL database backend, bootstrapping its own cluster."""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection

from database import postgres_cluster
from database.base import InternalDbSettings
from database.utils import (
    apply_missing_upgrades,
    apply_schema,
    connect,
    is_database_empty,
)


class InternalDb:
    """Database backend that owns and bootstraps a local PostgreSQL cluster."""

    def __init__(self, settings: InternalDbSettings) -> None:
        """Initialize the backend with its internal database settings.

        Args:
            settings: Internal database settings.

        """
        self.__settings = settings

    def prepare(self) -> None:
        """Bootstrap the cluster ahead of use.

        Initializes and starts the local PostgreSQL server if needed, then
        creates the application role and database if they are missing.
        """
        postgres_cluster.ensure_running(self.__settings)
        self._create_role_if_missing()
        self._create_database_if_missing()

    def check_connection(self) -> None:
        """Open and immediately close a connection to the database."""
        with connect(self.__settings):
            pass

    def initialize(self) -> None:
        """Apply the schema if the database is empty."""
        if is_database_empty(self.__settings):
            apply_schema(self.__settings)

    def upgrade(self) -> None:
        """Apply any missing upgrade scripts if the database is not empty."""
        if not is_database_empty(self.__settings):
            apply_missing_upgrades(self.__settings)

    def _admin_connect(self, *, database: str | None = None) -> connection:
        """Connect using admin credentials.

        Args:
            database: Database to connect to. Defaults to the configured
                admin database.

        Returns:
            An autocommit-enabled psycopg2 connection.

        """
        settings = self.__settings

        conn = psycopg2.connect(
            host=settings.host,
            port=settings.port,
            dbname=database or settings.admin_database,
            user=settings.admin_user,
            password=settings.admin_password,
        )
        conn.autocommit = True
        return conn

    def _create_role_if_missing(self) -> None:
        """Create the application login role if it does not already exist."""
        settings = self.__settings

        with self._admin_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s",
                (settings.user,),
            )
            if cur.fetchone() is not None:
                return

            cur.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(
                    sql.Identifier(settings.user)
                ),
                (settings.password,),
            )

    def _create_database_if_missing(self) -> None:
        """Create the application database, owned by its role, if missing."""
        settings = self.__settings

        with self._admin_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (settings.database,),
            )

            if cur.fetchone() is not None:
                return

            cur.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE {} OWNER {}").format(
                    sql.Identifier(settings.database),
                    sql.Identifier(settings.template),
                    sql.Identifier(settings.user),
                )
            )

        self._configure_new_database()

    def _configure_new_database(self) -> None:
        """Finish configuring a freshly created database.

        Reassigns ownership of the ``public`` schema to the application role
        and applies the optional cluster-wide ``max_connections`` tuning.
        """
        settings = self.__settings

        with (
            self._admin_connect(database=settings.database) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                sql.SQL("ALTER SCHEMA public OWNER TO {}").format(
                    sql.Identifier(settings.user)
                )
            )

            if settings.max_connections is not None:
                cur.execute(
                    "ALTER SYSTEM SET max_connections = %s",
                    (str(settings.max_connections),),
                )
