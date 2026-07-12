"""Base settings models and backend protocol for database configuration."""

from pathlib import Path
from typing import Annotated, Protocol

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict


class DbSettings(BaseModel):
    """Common connection and schema settings shared by all database backends."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )

    host: Annotated[str, Field(default="localhost")]
    port: Annotated[int, Field(default=5432)]

    database: str
    user: str
    password: str

    schema_path: Path
    upgrades_dir: Path | None = None
    target_version: str | None = None


class DatabaseBackend(Protocol):
    """Interface implemented by internal and external database backends."""

    def prepare(self) -> None:
        """Prepare the backend for use, verifying it is reachable."""
        ...

    def initialize(self) -> None:
        """Create the schema on a fresh, empty database."""
        ...

    def upgrade(self) -> None:
        """Apply any pending schema upgrades to an existing database."""
        ...

    def check_connection(self) -> None:
        """Verify that a connection to the database can be established."""
        ...


class InternalDbSettings(DbSettings):
    """Settings for a self-managed PostgreSQL instance owned by the installer."""

    admin_database: str = "postgres"
    admin_user: str = "postgres"
    admin_password: str
    template: str = "template0"

    pg_dir: Path
    pg_data: Path
    log_path: Path
    socket_dir: Path | None = None

    encoding: str = "UTF8"
    locale: str = "en_US.utf8"
    max_connections: int | None = None

    @property
    def pg_bin(self) -> Path:
        """Return the directory containing the PostgreSQL binaries."""
        return self.pg_dir / "bin"


class ExternalDbSettings(DbSettings):
    """Settings for connecting to a database managed outside the installer."""

    allow_schema_creation: bool = False
