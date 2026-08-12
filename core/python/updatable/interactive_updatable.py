"""Interactive updatable strategy: ask before dropping each broken symlink."""

from typing_extensions import override

from updatable.base import UpdatableBase
from workarea.utils import repair_broken_links


class InteractiveUpdatable(UpdatableBase):
    """Ask the user before removing each broken symlink, without reinstalling."""

    @override
    def __call__(self) -> None:
        repair_broken_links(self.workarea.work_root.rglob("*"), interactive=True)
