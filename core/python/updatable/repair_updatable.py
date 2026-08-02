"""Repair updatable strategy: drop broken symlinks, without reinstalling."""

from typing_extensions import override

from updatable.base import UpdatableBase
from workarea.utils import repair_broken_links


class RepairUpdatable(UpdatableBase):
    """Remove broken symlinks. Reinstalling is the caller's responsibility."""

    @override
    def __call__(self) -> None:
        repair_broken_links(self.workarea.work_root.rglob("*"))
