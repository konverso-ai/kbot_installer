"""Repair updater: drop broken symlinks before reinstalling."""

from typing_extensions import override

from installable.updater.base import UpdaterBase


class RepairUpdater(UpdaterBase):
    """Remove broken symlinks then reinstall the workarea."""

    @override
    def __call__(self) -> None:
        self.workarea.repair_broken_links()
        self.workarea.install()
