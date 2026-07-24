"""Tests for installable.updater.factory module."""

from unittest.mock import MagicMock

import pytest
from installable.updater.factory import UpdaterName, add_updater
from installable.updater.interactive_updater import InteractiveUpdater
from installable.updater.repair_updater import RepairUpdater
from installable.updater.smooth_updater import SmoothUpdater
from installable.updater.strict_updater import StrictUpdater


def test_updater_name_members() -> None:
    assert UpdaterName.STRICT == "strict"
    assert UpdaterName.SMOOTH == "smooth"
    assert UpdaterName.REPAIR == "repair"
    assert UpdaterName.INTERACTIVE == "interactive"


@pytest.mark.parametrize(
    ("name", "expected_class"),
    [
        (UpdaterName.STRICT.value, StrictUpdater),
        (UpdaterName.SMOOTH.value, SmoothUpdater),
        (UpdaterName.REPAIR.value, RepairUpdater),
        (UpdaterName.INTERACTIVE.value, InteractiveUpdater),
    ],
)
def test_add_updater_builds_expected_class(name: str, expected_class: type) -> None:
    workarea = MagicMock()

    updater = add_updater(name=name, workarea=workarea)

    assert isinstance(updater, expected_class)
    assert updater.workarea is workarea


def test_add_updater_raises_for_unknown_name() -> None:
    with pytest.raises(ImportError):
        add_updater(name="unknown", workarea=MagicMock())
