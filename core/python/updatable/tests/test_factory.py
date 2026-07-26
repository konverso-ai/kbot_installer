"""Tests for updatable.factory module."""

from unittest.mock import MagicMock

import pytest
from updatable.factory import UpdatableName, add_updatable
from updatable.interactive_updatable import InteractiveUpdatable
from updatable.repair_updatable import RepairUpdatable
from updatable.smooth_updatable import SmoothUpdatable
from updatable.strict_updatable import StrictUpdatable


def test_updatable_name_members() -> None:
    assert UpdatableName.STRICT == "strict"
    assert UpdatableName.SMOOTH == "smooth"
    assert UpdatableName.REPAIR == "repair"
    assert UpdatableName.INTERACTIVE == "interactive"


@pytest.mark.parametrize(
    ("name", "expected_class"),
    [
        (UpdatableName.STRICT.value, StrictUpdatable),
        (UpdatableName.SMOOTH.value, SmoothUpdatable),
        (UpdatableName.REPAIR.value, RepairUpdatable),
        (UpdatableName.INTERACTIVE.value, InteractiveUpdatable),
    ],
)
def test_add_updatable_builds_expected_class(name: str, expected_class: type) -> None:
    workarea = MagicMock()

    updatable = add_updatable(name=name, workarea=workarea)

    assert isinstance(updatable, expected_class)
    assert updatable.workarea is workarea


def test_add_updatable_raises_for_unknown_name() -> None:
    with pytest.raises(ImportError):
        add_updatable(name="unknown", workarea=MagicMock())
