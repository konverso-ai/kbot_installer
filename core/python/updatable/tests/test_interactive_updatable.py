"""Tests for updatable.interactive_updatable module."""

from unittest.mock import MagicMock

import pytest
from updatable.interactive_updatable import InteractiveUpdatable


def test_call_repairs_broken_links_interactively_without_reinstalling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workarea = MagicMock()
    repair_mock = MagicMock()
    monkeypatch.setattr("updatable.interactive_updatable.repair_broken_links", repair_mock)
    updatable = InteractiveUpdatable(workarea)

    updatable()

    repair_mock.assert_called_once_with(workarea.work_root.rglob.return_value, interactive=True)
    workarea.work_root.rglob.assert_called_once_with("*")
