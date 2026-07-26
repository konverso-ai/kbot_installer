"""Tests for updatable.smooth_updatable module."""

from unittest.mock import MagicMock

from updatable.smooth_updatable import SmoothUpdatable


def test_call_reinstalls_without_clearing() -> None:
    workarea = MagicMock()
    updatable = SmoothUpdatable(workarea)

    updatable()

    workarea.clear.assert_not_called()
    workarea.install.assert_called_once_with()
