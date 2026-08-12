"""Base interface for Workarea updatable strategies."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workarea.workarea import Workarea


class UpdatableBase(ABC):
    """Base interface for updatable strategies applied to a Workarea."""

    def __init__(self, workarea: "Workarea") -> None:
        """Bind the updater to the workarea it will update.

        Args:
            workarea: The `Workarea` model this updater strategy operates on.

        """
        self.workarea = workarea

    @abstractmethod
    def __call__(self) -> None:
        """Run the update strategy against the workarea."""
