"""Nexus credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

NexusUsername: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias=AliasChoices("NEXUS_USERNAME", "NEXUS_USER")),
]
NexusPassword: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="NEXUS_PASSWORD"),
]


class NexusCredentials(BaseSettings):
    """Nexus HTTP credentials loaded from the environment."""

    model_config = SettingsConfigDict(extra="ignore")

    username: NexusUsername
    password: NexusPassword

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            Names of the Nexus environment variables that are not set.

        """
        missing: list[str] = []
        if not self.username:
            missing.append("NEXUS_USERNAME")
        if not self.password:
            missing.append("NEXUS_PASSWORD")
        return missing

    def auth_kwargs(self) -> dict[str, object]:
        """Return keyword arguments for ``add_http_auth("basic", **kwargs)``."""
        if not self.username or not self.password:
            return {}
        return {"username": self.username, "password": self.password}
