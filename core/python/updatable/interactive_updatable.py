"""Interactive updatable strategy: ask before dropping each broken symlink."""

from typing_extensions import override

from updatable.base import UpdatableBase


class InteractiveUpdatable(UpdatableBase):
    """Ask the user before removing each broken symlink, without reinstalling."""

    @override
    def __call__(self) -> None:
        self.workarea.repair_broken_links(interactive=True)
