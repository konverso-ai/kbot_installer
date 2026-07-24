"""Tests for installable.updater.base module."""

from unittest.mock import MagicMock

import pytest
from installable.updater.base import UpdaterBase
from typing_extensions import override


def test_cannot_instantiate_abstract_base_directly() -> None:
    with pytest.raises(TypeError):
        UpdaterBase(MagicMock())


def test_subclass_stores_workarea_and_is_callable() -> None:
    workarea = MagicMock()

    class DummyUpdater(UpdaterBase):
        @override
        def __call__(self) -> None:
            self.workarea.install()

    updater = DummyUpdater(workarea)
    updater()

    assert updater.workarea is workarea
    workarea.install.assert_called_once_with()


def test_subclass_without_call_remains_abstract() -> None:
    class IncompleteUpdater(UpdaterBase):
        pass

    with pytest.raises(TypeError):
        IncompleteUpdater(MagicMock())
