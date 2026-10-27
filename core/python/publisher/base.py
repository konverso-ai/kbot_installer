"""Base publisher protocol for bundle publication."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from utils.bundle import Bundle


class PublisherBase(Protocol):
    """Publisher base protocol."""

    def publish(self, bundle: Bundle) -> None:
        """Publish a bundle."""
