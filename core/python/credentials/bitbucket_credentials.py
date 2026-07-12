"""Bitbucket credentials loaded from the environment."""

from typing import Annotated, TypeAlias, cast

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BitbucketUsername: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="BITBUCKET_USERNAME"),
]
BitbucketPassword: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="BITBUCKET_APP_PASSWORD"),
]


class BitbucketCredentials(BaseSettings):
    """Bitbucket credentials loaded from the environment."""

    model_config = SettingsConfigDict(extra="ignore")

    username: BitbucketUsername
    password: BitbucketPassword

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            Names of the Bitbucket environment variables that are not set.

        """
        missing: list[str] = []
        if not self.username:
            missing.append("BITBUCKET_USERNAME")
        if not self.password:
            missing.append("BITBUCKET_APP_PASSWORD")
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
