"""Tests for installable.updater.strict_updater module."""

from unittest.mock import MagicMock, call

from installable.updater.strict_updater import StrictUpdater


def test_call_clears_before_reinstalling() -> None:
    workarea = MagicMock()
    updater = StrictUpdater(workarea)

    updater()

    workarea.clear.assert_called_once_with()
    workarea.install.assert_called_once_with()
    assert workarea.method_calls == [call.clear(), call.install()]
