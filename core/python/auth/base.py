"""Base model for authentication fields."""

from abc import abstractmethod
from collections.abc import Iterator, Mapping
from typing import Annotated, TypeAlias

import httpx
from pydantic import BaseModel, Field, SecretStr
from typing_extensions import override

HeaderName: TypeAlias = Annotated[str, Field(default="Authorization")]
Prefix: TypeAlias = Annotated[str, Field(default="")]
Secret: TypeAlias = Annotated[SecretStr, Field(default=SecretStr(""))]
RequiredSecret: TypeAlias = Annotated[SecretStr, Field(min_length=1)]
RemoteKwargs: TypeAlias = dict[str, str]


class HttpAuthBase(BaseModel, httpx.Auth):
    """Shared authentication fields for header-based auth."""

    header_name: HeaderName
    prefix: Prefix
    secret: Secret

    @abstractmethod
    @override
    def auth_flow(self, request: httpx.Request) -> Iterator[httpx.Request]:
        """Apply authentication to an outgoing HTTP request."""

    @abstractmethod
    def remote_kwargs(self) -> RemoteKwargs:
        """Return keyword arguments for Dulwich remote operations."""

    def git_cli_environment(
        self, _base_env: Mapping[str, str] | None = None
    ) -> dict[str, str] | None:
        """Return environment for git subprocess operations, if supported."""
        return None
