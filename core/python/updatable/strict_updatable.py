"""Strict updatable strategy: clear the workarea before reinstalling."""

from typing_extensions import override

from updatable.base import UpdatableBase


class StrictUpdatable(UpdatableBase):
    """Clear the workarea then reinstall it from scratch."""

    @override
    def __call__(self) -> None:
        self.workarea.clear()
        self.workarea.install()
