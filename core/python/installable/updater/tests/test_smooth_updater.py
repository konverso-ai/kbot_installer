"""Tests for installable.updater.smooth_updater module."""

from unittest.mock import MagicMock

from installable.updater.smooth_updater import SmoothUpdater


def test_call_reinstalls_without_clearing() -> None:
    workarea = MagicMock()
    updater = SmoothUpdater(workarea)

    updater()

    workarea.clear.assert_not_called()
    workarea.install.assert_called_once_with()
