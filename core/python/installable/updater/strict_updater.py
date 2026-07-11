"""Strict updater: clear the workarea before reinstalling."""

from typing_extensions import override

from installable.updater.base import UpdaterBase


class StrictUpdater(UpdaterBase):
    """Clear the workarea then reinstall it from scratch."""

    @override
    def __call__(self) -> None:
        self.workarea.clear()
        self.workarea.install()
