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
        """Return canonical environment variable names that are absent.

        Returns:
            An empty list when ``GITHUB_TOKEN`` is set, otherwise a list
            containing ``GITHUB_TOKEN``.

        """
        return [] if self.token else ["GITHUB_TOKEN"]

    def auth_kwargs(self) -> dict[str, str] | None:
        """Return HTTP auth constructor kwargs when credentials are complete.

        Returns:
            A mapping with ``username`` and ``password`` (the token), or None
            if the token is missing.

        """
        if not self.token:
            return None
        return {"username": "git", "password": self.token}
