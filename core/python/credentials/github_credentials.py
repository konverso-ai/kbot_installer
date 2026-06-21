"""GitHub credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

GithubToken: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="GITHUB_TOKEN"),
]


class GithubCredentials(BaseSettings):
    """GitHub credentials loaded from the environment."""

    model_config = SettingsConfigDict(extra="ignore")

    token: GithubToken

    def missing_env_vars(self) -> list[str]:
        return [] if self.token else ["GITHUB_TOKEN"]

    def auth_kwargs(self) -> dict[str, str] | None:
        if not self.token:
            return None
        return {"username": "git", "password": self.token}
