"""Tests for updatable.workarea_updatable module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from updatable.factory import UpdatableName
from updatable.workarea_updatable import WorkareaUpdatable
from workarea.workarea import Workarea


def _workarea(tmp_path: Path, **overrides: object) -> Workarea:
    defaults: dict[str, object] = {
        "installer_root": tmp_path / "installer",
        "work_root": tmp_path / "work",
        "products": [],
    }
    defaults.update(overrides)
    return Workarea(**defaults)


def test_call_dispatches_to_updatable_matching_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workarea = _workarea(tmp_path)
    strategy = MagicMock()
    add_updatable = MagicMock(return_value=strategy)
    monkeypatch.setattr("updatable.workarea_updatable.add_updatable", add_updatable)

    WorkareaUpdatable(workarea=workarea, mode=UpdatableName.STRICT)()

    add_updatable.assert_called_once_with(name=UpdatableName.STRICT.value, workarea=workarea)
    strategy.assert_called_once_with()


def test_call_is_a_noop_for_smooth_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workarea = _workarea(tmp_path)
    add_updatable = MagicMock()
    monkeypatch.setattr("updatable.workarea_updatable.add_updatable", add_updatable)

    WorkareaUpdatable(workarea=workarea, mode=UpdatableName.SMOOTH)()

    add_updatable.assert_not_called()


class TestEndToEnd:
    def test_strict_mode_clears_the_work_root(self, tmp_path: Path) -> None:
        workarea = _workarea(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        (work_root / "stray.txt").write_text("removed")

        WorkareaUpdatable(workarea=workarea, mode=UpdatableName.STRICT)()

        assert work_root.exists()
        assert list(work_root.iterdir()) == []

    def test_repair_mode_removes_broken_links(self, tmp_path: Path) -> None:
        workarea = _workarea(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken = work_root / "broken_link"
        broken.symlink_to(work_root / "does_not_exist")

        WorkareaUpdatable(workarea=workarea, mode=UpdatableName.REPAIR)()

        assert not broken.exists()

    def test_interactive_mode_removes_broken_links_after_confirmation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workarea = _workarea(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken = work_root / "broken_link"
        broken.symlink_to(work_root / "does_not_exist")
        monkeypatch.setattr("builtins.input", lambda _prompt: "y")

        WorkareaUpdatable(workarea=workarea, mode=UpdatableName.INTERACTIVE)()

        assert not broken.exists()

    def test_smooth_mode_leaves_the_work_root_untouched(self, tmp_path: Path) -> None:
        workarea = _workarea(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        stray = work_root / "stray.txt"
        stray.write_text("kept")

        WorkareaUpdatable(workarea=workarea, mode=UpdatableName.SMOOTH)()

        assert stray.exists()
