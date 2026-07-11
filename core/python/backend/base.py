"""Base class for backend services."""

from typing import Any, Protocol


class BackendBase(Protocol):
    """Abstract base class for backend services."""

    def get_client(self) -> Any | None:
        """Return the service client managed by this backend."""
