"""Base module for SSH authentication strategies."""

from abc import abstractmethod
from collections.abc import Iterator, Mapping
from typing import TypeAlias

import httpx
from pydantic import BaseModel
from typing_extensions import override

RemoteKwargs: TypeAlias = dict[str, str]


class SshAuthBase(BaseModel, httpx.Auth):
    """Shared behaviour for SSH authentication strategies.

    Self-contained base for the ``auth.ssh`` package: it has no dependency on
    ``auth.http`` or any shared top-level ``auth`` module. Unlike HTTP auth,
    SSH authentication never sets an HTTP header, so ``auth_flow`` is a
    concrete no-op here rather than an abstract method.
    """

    @override
    def auth_flow(self, request: httpx.Request) -> Iterator[httpx.Request]:
        yield request

    @abstractmethod
    def remote_kwargs(self) -> RemoteKwargs:
        """Return keyword arguments for Dulwich remote operations."""

    def git_cli_environment(
        self,
        base_env: Mapping[str, str] | None = None,  # noqa: ARG002
    ) -> dict[str, str] | None:
        """Return environment for git subprocess operations, if supported."""
        return None
