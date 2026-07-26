"""Tests for updatable.interactive_updatable module."""

from unittest.mock import MagicMock

from updatable.interactive_updatable import InteractiveUpdatable


def test_call_repairs_broken_links_interactively_without_reinstalling() -> None:
    workarea = MagicMock()
    updatable = InteractiveUpdatable(workarea)

    updatable()

    workarea.repair_broken_links.assert_called_once_with(interactive=True)
    workarea.install.assert_not_called()
