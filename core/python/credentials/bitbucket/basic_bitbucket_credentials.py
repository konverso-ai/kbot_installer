"""Basic (username/app-password) Bitbucket credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BitbucketUsername: TypeAlias = Annotated[
    str | None,
    Field(default=None),
]
BitbucketPassword: TypeAlias = Annotated[
    SecretStr | None,
    Field(default=None, validation_alias="BITBUCKET_APP_PASSWORD"),
]


class BasicBitbucketCredentials(BaseSettings):
    """Bitbucket credentials for HTTP basic authentication."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="BITBUCKET_"
    )

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

    def auth_kwargs(self) -> dict[str, object]:
        """Return keyword arguments for ``add_http_auth("basic", **kwargs)``."""
        if not self.username or not self.password:
            return {}
        return {
            "username": self.username,
            "password": self.password.get_secret_value(),
        }
