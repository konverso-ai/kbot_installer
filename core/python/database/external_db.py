from database.base import ExternalDbSettings
from database.utils import (
    apply_missing_upgrades,
    apply_schema,
    connect,
    is_database_empty,
)


class ExternalDb:
    def __init__(self, settings: ExternalDbSettings) -> None:
        self.__settings = settings

    def prepare(self) -> None:
        self.check_connection()

    def check_connection(self) -> None:
        with connect(self.__settings):
            pass

    def _check_is_empty(self) -> bool:
        empty = is_database_empty(self.__settings)

        if empty and not self.__settings.allow_schema_creation:
            msg = "External database is empty, but schema creation si disabled"
            raise RuntimeError(msg)
        return empty

    def initialize(self) -> None:
        if self._check_is_empty():
            apply_schema(self.__settings)

    def upgrade(self) -> None:
        if not self._check_is_empty():
            apply_missing_upgrades(self.__settings)
