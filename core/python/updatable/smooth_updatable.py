"""Smooth updatable strategy: reinstall on top of the existing workarea."""

from typing_extensions import override

from updatable.base import UpdatableBase


class SmoothUpdatable(UpdatableBase):
    """Reinstall the workarea, leaving existing files and links untouched."""

    @override
    def __call__(self) -> None:
        self.workarea.install()
