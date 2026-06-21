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
        missing: list[str] = []
        if not self.username:
            missing.append("BITBUCKET_USERNAME")
        if not self.password:
            missing.append("BITBUCKET_APP_PASSWORD")
        return missing

    def auth_kwargs(self) -> dict[str, str] | None:
        if self.missing_env_vars():
            return None
        return cast(
            dict[str, str],
            {"username": self.username, "password": self.password},
        )
