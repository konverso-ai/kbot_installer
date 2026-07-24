"""Interactive updater: ask before dropping each broken symlink."""

from typing_extensions import override

from installable.updater.base import UpdaterBase


class InteractiveUpdater(UpdaterBase):
    """Ask the user before removing each broken symlink, without reinstalling."""

    @override
    def __call__(self) -> None:
        self.workarea.repair_broken_links(interactive=True)
