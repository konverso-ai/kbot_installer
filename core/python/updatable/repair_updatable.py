"""Repair updatable strategy: drop the product links and broken symlinks, without reinstalling."""

from typing_extensions import override

from updatable.base import UpdatableBase
from workarea.utils import remove_installer_links, repair_broken_links


class RepairUpdatable(UpdatableBase):
    """Remove every link into the installer, then the remaining broken symlinks.

    Valid product links are dropped too, so the reinstall relinks every path
    from the product that currently provides it (e.g. after an upgrade). Regular
    files (database, logs, copies) are kept. Reinstalling is the caller's
    responsibility.
    """

    @override
    def __call__(self) -> None:
        remove_installer_links(self.workarea.work_root, self.workarea.installer_root)
        repair_broken_links(self.workarea.work_root.rglob("*"))
