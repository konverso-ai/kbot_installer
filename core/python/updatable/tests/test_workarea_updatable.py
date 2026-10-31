"""Tests for updatable.workarea_updatable module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from installable.workarea_installable import WorkareaInstallable
from updatable.factory import UpdatableName
from updatable.workarea_updatable import WorkareaUpdatable
from workarea.workarea import Workarea


def _installable(tmp_path: Path, **overrides: object) -> WorkareaInstallable:
    defaults: dict[str, object] = {
        "installer_root": tmp_path / "installer",
        "work_root": tmp_path / "work",
        "products": [],
    }
    defaults.update(overrides)
    return WorkareaInstallable(workarea=Workarea(**defaults))


@pytest.fixture(autouse=True)
def _skip_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """WorkareaInstallable.install() is exercised by installable/tests already."""
    monkeypatch.setattr(WorkareaInstallable, "install", MagicMock())


def test_call_dispatches_to_updatable_matching_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installable = _installable(tmp_path)
    strategy = MagicMock()
    add_updatable = MagicMock(return_value=strategy)
    monkeypatch.setattr("updatable.workarea_updatable.add_updatable", add_updatable)

    WorkareaUpdatable(installable=installable, mode=UpdatableName.STRICT)()

    add_updatable.assert_called_once_with(name=UpdatableName.STRICT.value, workarea=installable.workarea)
    strategy.assert_called_once_with()
    installable.install.assert_called_once_with()


def test_call_skips_the_strategy_for_smooth_mode_but_still_reinstalls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installable = _installable(tmp_path)
    add_updatable = MagicMock()
    monkeypatch.setattr("updatable.workarea_updatable.add_updatable", add_updatable)

    WorkareaUpdatable(installable=installable, mode=UpdatableName.SMOOTH)()

    add_updatable.assert_not_called()
    installable.install.assert_called_once_with()


class TestEndToEnd:
    def test_strict_mode_clears_the_work_root_then_reinstalls(self, tmp_path: Path) -> None:
        installable = _installable(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        (work_root / "stray.txt").write_text("removed")

        WorkareaUpdatable(installable=installable, mode=UpdatableName.STRICT)()

        assert work_root.exists()
        assert list(work_root.iterdir()) == []
        installable.install.assert_called_once_with()

    def test_repair_mode_removes_broken_links_then_reinstalls(self, tmp_path: Path) -> None:
        installable = _installable(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken = work_root / "broken_link"
        broken.symlink_to(work_root / "does_not_exist")

        WorkareaUpdatable(installable=installable, mode=UpdatableName.REPAIR)()

        assert not broken.exists()
        installable.install.assert_called_once_with()

    def test_interactive_mode_removes_broken_links_after_confirmation_then_reinstalls(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        installable = _installable(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken = work_root / "broken_link"
        broken.symlink_to(work_root / "does_not_exist")
        monkeypatch.setattr("builtins.input", lambda _prompt: "y")

        WorkareaUpdatable(installable=installable, mode=UpdatableName.INTERACTIVE)()

        assert not broken.exists()
        installable.install.assert_called_once_with()

    def test_smooth_mode_leaves_the_work_root_untouched_but_reinstalls(self, tmp_path: Path) -> None:
        installable = _installable(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        stray = work_root / "stray.txt"
        stray.write_text("kept")

        WorkareaUpdatable(installable=installable, mode=UpdatableName.SMOOTH)()

        assert stray.exists()
        installable.install.assert_called_once_with()
