"""Tests for updatable.repair_updatable module."""

from unittest.mock import MagicMock

import pytest
from updatable.repair_updatable import RepairUpdatable


def test_call_repairs_broken_links_without_reinstalling(monkeypatch: pytest.MonkeyPatch) -> None:
    workarea = MagicMock()
    repair_mock = MagicMock()
    monkeypatch.setattr("updatable.repair_updatable.repair_broken_links", repair_mock)
    updatable = RepairUpdatable(workarea)

    updatable()

    repair_mock.assert_called_once_with(workarea.work_root.rglob.return_value)
    workarea.work_root.rglob.assert_called_once_with("*")
