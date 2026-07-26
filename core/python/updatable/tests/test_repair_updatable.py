"""Tests for updatable.repair_updatable module."""

from unittest.mock import MagicMock, call

from updatable.repair_updatable import RepairUpdatable


def test_call_repairs_broken_links_before_reinstalling() -> None:
    workarea = MagicMock()
    updatable = RepairUpdatable(workarea)

    updatable()

    workarea.repair_broken_links.assert_called_once_with()
    workarea.install.assert_called_once_with()
    assert workarea.method_calls == [call.repair_broken_links(), call.install()]
