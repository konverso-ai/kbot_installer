"""Tests for installable.updater.repair_updater module."""

from unittest.mock import MagicMock, call

from installable.updater.repair_updater import RepairUpdater


def test_call_repairs_broken_links_before_reinstalling() -> None:
    workarea = MagicMock()
    updater = RepairUpdater(workarea)

    updater()

    workarea.repair_broken_links.assert_called_once_with()
    workarea.install.assert_called_once_with()
    assert workarea.method_calls == [call.repair_broken_links(), call.install()]
