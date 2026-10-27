"""Basic (token) GitHub credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

GithubUsername: TypeAlias = Annotated[
    str | None,
    Field(default=None),
]
GithubToken: TypeAlias = Annotated[
    SecretStr | None,
    Field(default=None),
]


class BasicGithubCredentials(BaseSettings):
    """GitHub credentials for HTTP basic (token) authentication."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="GITHUB_",
    )

    username: GithubUsername
    token: GithubToken

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            An empty list when ``GITHUB_TOKEN`` is set, otherwise a list
            containing ``GITHUB_TOKEN``.

        """
        return [] if self.token else ["GITHUB_TOKEN"]

    def auth_kwargs(self) -> dict[str, object]:
        """Return keyword arguments for ``add_http_auth("basic", **kwargs)``."""
        if not self.token:
            return {}
        return {
            "username": self.username or "x-access-token",
            "password": self.token.get_secret_value(),
        }
