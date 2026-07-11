from pathlib import Path
from typing import Annotated, Protocol

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict


class DbSettings(BaseModel):
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

    pg_dir: Path

    @property
    def pg_bin(self) -> Path:
        return self.pg_dir / "bin"


class DatabaseBackend(Protocol):
    def prepare(self) -> None: ...
    def initialize(self) -> None: ...
    def upgrade(self) -> None: ...
    def check_connection(self) -> None: ...


class InternalDbSettings(DbSettings):
    admin_database: str = "postgres"
    admin_user: str = "postgres"
    admin_password: str
    template: str = "template0"


class ExternalDbSettings(DbSettings):
    allow_schema_creation: bool = False
