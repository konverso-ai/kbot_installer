"""Strict updatable strategy: clear the workarea, without reinstalling."""

from typing_extensions import override

from updatable.base import UpdatableBase
from workarea.utils import clear_workarea


class StrictUpdatable(UpdatableBase):
    """Clear the workarea. Reinstalling is the caller's responsibility."""

    @override
    def __call__(self) -> None:
        clear_workarea(self.workarea.work_root)
