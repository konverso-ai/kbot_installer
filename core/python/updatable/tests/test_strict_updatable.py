"""Tests for updatable.strict_updatable module."""

from unittest.mock import MagicMock, call

from updatable.strict_updatable import StrictUpdatable


def test_call_clears_before_reinstalling() -> None:
    workarea = MagicMock()
    updatable = StrictUpdatable(workarea)

    updatable()

    workarea.clear.assert_called_once_with()
    workarea.install.assert_called_once_with()
    assert workarea.method_calls == [call.clear(), call.install()]
