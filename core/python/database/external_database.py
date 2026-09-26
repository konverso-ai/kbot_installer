"""Database backend for externally managed PostgreSQL instances."""

from pathlib import Path
from typing import ClassVar

from database.base import ExternalDbSettings
from database.utils import (
    apply_missing_upgrades,
    apply_schema,
    connect,
    drop_owned_objects,
    dump_database,
    is_database_empty,
)


class ExternalDatabase:
    """Database backend that connects to a database managed outside the installer."""

    settings_cls: ClassVar[type[ExternalDbSettings]] = ExternalDbSettings

    def __init__(self, settings: ExternalDbSettings) -> None:
        """Initialize the backend with its connection and schema settings.

        Args:
            settings: Connection and schema settings for the external database.

        """
        self.__settings = settings

    def prepare(self) -> None:
        """Verify that the external database is reachable."""
        self.check_connection()

    def check_connection(self) -> None:
        """Open and immediately close a connection to check reachability."""
        with connect(self.__settings):
            pass

    def _check_is_empty(self) -> bool:
        """Check whether the database has no tables yet.

        Returns:
            True if the database is empty, False otherwise.

        Raises:
            RuntimeError: If the database is empty but schema creation is disabled.

        """
        empty = is_database_empty(self.__settings)

        if empty and not self.__settings.allow_schema_creation:
            msg = "External database is empty, but schema creation si disabled"
            raise RuntimeError(msg)
        return empty

    def initialize(self) -> None:
        """Create the schema if the database is empty."""
        if self._check_is_empty():
            apply_schema(self.__settings)

    def upgrade(self) -> None:
        """Apply any pending schema upgrades if the database is not empty."""
        if not self._check_is_empty():
            apply_missing_upgrades(self.__settings)

    def backup(self, path: Path) -> bool:
        """Dump the database into a SQL file.

        Args:
            path: SQL file to write.

        Returns:
            Always True: an external database always exists.

        """
        dump_database(self.__settings, path)
        return True

    def destroy(self) -> None:
        """Drop every object owned by the application user.

        The database itself and the user are left in place: deleting them
        requires the external PostgreSQL server's administrator.
        """
        drop_owned_objects(self.__settings)
