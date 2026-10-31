"""Base class for backend services."""

from typing import Protocol


class BackendBase(Protocol):
    """Abstract base class for backend services."""

    def get_client(self) -> object | None:
        """Return the service client managed by this backend."""
