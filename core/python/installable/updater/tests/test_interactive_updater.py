"""Tests for installable.updater.interactive_updater module."""

from unittest.mock import MagicMock

from installable.updater.interactive_updater import InteractiveUpdater


def test_call_repairs_broken_links_interactively_without_reinstalling() -> None:
    workarea = MagicMock()
    updater = InteractiveUpdater(workarea)

    updater()

    workarea.repair_broken_links.assert_called_once_with(interactive=True)
    workarea.install.assert_not_called()
