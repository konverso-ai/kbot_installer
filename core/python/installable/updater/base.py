"""Base interface for WorkareaInstallable updaters."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from installable.workarea_installable import WorkareaInstallable


class UpdaterBase(ABC):
    """Base interface for updater strategies applied to a WorkareaInstallable."""

    def __init__(self, workarea: "WorkareaInstallable") -> None:
        self.workarea = workarea

    @abstractmethod
    def __call__(self) -> None:
        """Run the update strategy against the workarea."""
