"""Mixin providing HTTP and Dulwich authentication behaviour."""

from collections.abc import Iterator
from typing import TypeAlias

import httpx
from pydantic import computed_field

from auth.base import AuthBase

RemoteKwargs: TypeAlias = dict[str, str]


class AuthMixin(AuthBase):
    """Authentication behaviour shared by all auth implementations."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def header_value(self) -> str:
        secret = self.secret.get_secret_value()
        if self.prefix:
            return f"{self.prefix} {secret}"
        return secret

    def auth_flow(self, request: httpx.Request) -> Iterator[httpx.Request]:
        request.headers[self.header_name] = self.header_value
        yield request

    def remote_kwargs(self) -> RemoteKwargs:
        return {}
