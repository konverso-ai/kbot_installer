"""Tests for updatable.strict_updatable module."""

from unittest.mock import MagicMock

import pytest
from updatable.strict_updatable import StrictUpdatable


def test_call_clears_the_workarea_without_reinstalling(monkeypatch: pytest.MonkeyPatch) -> None:
    workarea = MagicMock()
    clear_mock = MagicMock()
    monkeypatch.setattr("updatable.strict_updatable.clear_workarea", clear_mock)
    updatable = StrictUpdatable(workarea)

    updatable()

    clear_mock.assert_called_once_with(workarea.work_root)
