"""Base model for authentication fields."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Annotated, TypeAlias

import httpx
from pydantic import BaseModel, Field, SecretStr

HeaderName: TypeAlias = Annotated[str, Field(default="Authorization")]
Prefix: TypeAlias = Annotated[str, Field(default="")]
Secret: TypeAlias = Annotated[SecretStr, Field(default=SecretStr(""))]
RequiredSecret: TypeAlias = Annotated[SecretStr, Field(min_length=1)]
RemoteKwargs: TypeAlias = dict[str, str]


class AuthBase(BaseModel, httpx.Auth, ABC):
    """Shared authentication fields for header-based auth."""

    header_name: HeaderName
    prefix: Prefix
    secret: Secret

    @abstractmethod
    def auth_flow(self, request: httpx.Request) -> Iterator[httpx.Request]:
        """Apply authentication to an outgoing HTTP request."""

    @abstractmethod
    def remote_kwargs(self) -> RemoteKwargs:
        """Return keyword arguments for Dulwich remote operations."""
