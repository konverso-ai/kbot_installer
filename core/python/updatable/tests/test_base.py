"""Tests for updatable.base module."""

from unittest.mock import MagicMock

import pytest
from typing_extensions import override
from updatable.base import UpdatableBase


def test_cannot_instantiate_abstract_base_directly() -> None:
    with pytest.raises(TypeError):
        UpdatableBase(MagicMock())


def test_subclass_stores_workarea_and_is_callable() -> None:
    workarea = MagicMock()

    class DummyUpdatable(UpdatableBase):
        @override
        def __call__(self) -> None:
            self.workarea.install()

    updatable = DummyUpdatable(workarea)
    updatable()

    assert updatable.workarea is workarea
    workarea.install.assert_called_once_with()


def test_subclass_without_call_remains_abstract() -> None:
    class IncompleteUpdatable(UpdatableBase):
        pass

    with pytest.raises(TypeError):
        IncompleteUpdatable(MagicMock())
