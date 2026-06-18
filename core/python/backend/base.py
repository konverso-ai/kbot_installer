"""Base class for backend services."""

from abc import ABC, abstractmethod
from typing import Any


class BackendBase(ABC):
    """Abstract base class for backend services."""

    @abstractmethod
    def get_client(self) -> Any | None:
        """Return the service client managed by this backend."""
