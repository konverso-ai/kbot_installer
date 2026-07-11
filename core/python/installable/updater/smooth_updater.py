"""Smooth updater: reinstall on top of the existing workarea."""

from typing_extensions import override

from installable.updater.base import UpdaterBase


class SmoothUpdater(UpdaterBase):
    """Reinstall the workarea, leaving existing files and links untouched."""

    @override
    def __call__(self) -> None:
        self.workarea.install()
