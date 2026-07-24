"""Basic HTTP authentication (username and password)."""

import base64
from typing import Annotated, TypeAlias

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self, override

from auth.auth_mixin import AuthMixin
from auth.base import RemoteKwargs

BasicPrefix: TypeAlias = Annotated[str, Field(default="Basic")]

Username: TypeAlias = Annotated[str, Field(min_length=1)]
Password: TypeAlias = Annotated[SecretStr, Field(min_length=1)]


class BasicAuth(AuthMixin, BaseSettings):
    """Authentication using HTTP Basic (username and password).

    Credentials are base64-encoded into ``secret`` for the Authorization header.
    ``remote_kwargs`` exposes plain username/password for Dulwich HTTP(S) remotes.

    ``username`` and ``password`` can be passed explicitly or read from the
    environment (``BASIC_AUTH_USERNAME``, ``BASIC_AUTH_PASSWORD``). Explicit
    values take precedence over environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="BASIC_AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    prefix: BasicPrefix
    username: Username
    password: Password

    @model_validator(mode="after")
    def encode_secret(self) -> Self:
        """Derive the base64-encoded Basic auth secret from username and password.

        Returns:
            The model instance with ``secret`` populated.

        """
        credentials = f"{self.username}:{self.password.get_secret_value()}"
        encoded = base64.b64encode(credentials.encode()).decode("ascii")
        self.secret = SecretStr(encoded)
        return self

    @override
    def remote_kwargs(self) -> RemoteKwargs:
        return {
            "username": self.username,
            "password": self.password.get_secret_value(),
        }
