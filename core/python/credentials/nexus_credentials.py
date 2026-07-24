"""Nexus credentials loaded from the environment."""

from typing import Annotated, TypeAlias, cast

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

    def auth_kwargs(self) -> dict[str, str] | None:
        """Return HTTP auth constructor kwargs when credentials are complete.

        Returns:
            A mapping with ``username`` and ``password``, or None if either is
            missing.

        """
        if self.missing_env_vars():
            return None
        return cast(
            "dict[str, str]",
            {"username": self.username, "password": self.password},
        )
