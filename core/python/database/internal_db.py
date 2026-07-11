import psycopg2
from psycopg2 import sql

from database.base import InternalDbSettings
from database.utils import (
    apply_missing_upgrades,
    apply_schema,
    connect,
    is_database_empty,
)


class InternalDb:
    def __init__(self, settings: InternalDbSettings) -> None:
        self.__settings = settings

    def prepare(self) -> None:
        self._create_database_if_missing()

    def check_connection(self) -> None:
        with connect(self.__settings):
            pass

    def initialize(self) -> None:
        if is_database_empty(self.__settings):
            apply_schema(self.__settings)

    def upgrade(self) -> None:
        if not is_database_empty(self.__settings):
            apply_missing_upgrades(self.__settings)

    def _create_database_if_missing(self) -> None:
        settings = self.__settings

        with psycopg2.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.admin_database,
            user=settings.admin_user,
            password=settings.admin_password,
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (settings.database,),
                )

                exists = cur.fetchone() is not None
                if exists:
                    return

                cur.execute(
                    sql.SQL(
                        f"CREATE DATABASE {sql.Identifier(settings.database)} TEMPLATE {sql.Identifier(settings.template)}"
                    )
                )
