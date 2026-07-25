"""Structural protocol for authentication objects usable in git operations."""

from collections.abc import Iterator, Mapping
from typing import Protocol, runtime_checkable

import httpx

RemoteKwargs = dict[str, str]


@runtime_checkable
class GitAuthProtocol(Protocol):
    """Authentication contract required by git versioners and providers.

    Both ``auth.http`` and ``auth.ssh`` implementations satisfy this protocol
    structurally (no shared base class needed): anything that behaves like an
    ``httpx.Auth`` (has ``auth_flow``) and also exposes
    ``remote_kwargs``/``git_cli_environment`` can be passed to
    :mod:`git.versioner` and :mod:`git.provider`. A ``Protocol`` cannot
    inherit from a concrete class such as ``httpx.Auth``, so ``auth_flow`` is
    declared here structurally instead.
    """

    def auth_flow(self, request: httpx.Request) -> Iterator[httpx.Request]:
        """Apply authentication to an outgoing HTTP request."""
        ...

    def remote_kwargs(self) -> RemoteKwargs:
        """Return keyword arguments for Dulwich remote operations."""
        ...

    def git_cli_environment(
        self, base_env: Mapping[str, str] | None = None
    ) -> dict[str, str] | None:
        """Return environment for git subprocess operations, if supported."""
        ...
