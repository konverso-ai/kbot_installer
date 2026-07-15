"""Tests for WorkareaInstallable."""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from installable.updater.factory import UpdaterName
from installable.workarea_installable import WorkareaInstallable
from workarea.rule_action import RuleAction
from workarea.workarea import Workarea
from workarea.workarea_rule import WorkareaRule


def _build(
    tmp_path: Path,
    *,
    products: list[Path] | None = None,
    rules: list[WorkareaRule] | None = None,
    update_mode: UpdaterName = UpdaterName.SMOOTH,
) -> WorkareaInstallable:
    return WorkareaInstallable(
        workarea=Workarea(
            installer_root=tmp_path / "installer",
            work_root=tmp_path / "work",
            products=products or [],
            rules=rules or [],
        ),
        update_mode=update_mode,
    )


@pytest.fixture(autouse=True)
def _skip_tests_dir_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    """cleanup_unused_tests_dir is exercised by workarea/tests/test_utils.py already."""
    monkeypatch.setattr(
        "installable.workarea_installable.cleanup_unused_tests_dir",
        lambda *args, **kwargs: None,
    )


class TestInstall:
    def test_creates_work_root_and_runtime_dirs(self, tmp_path: Path) -> None:
        wa = _build(tmp_path)

        wa.install()

        work_root = tmp_path / "work"
        assert work_root.is_dir()
        assert (work_root / "conf" / "kbot.conf").exists()
        assert (work_root / "logs" / "httpd").is_dir()
        assert (work_root / "var" / "pkl" / "storage").is_dir()
        assert (work_root / "products").is_dir()

    def test_applies_rules_for_existing_products(self, tmp_path: Path) -> None:
        product_dir = tmp_path / "installer" / "productA"
        (product_dir / "core").mkdir(parents=True)
        (product_dir / "core" / "file.py").write_text("data")

        rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)
        wa = _build(tmp_path, products=[Path("productA")], rules=[rule])

        wa.install()

        link = tmp_path / "work" / "core" / "file.py"
        assert link.is_symlink()
        assert link.resolve() == (product_dir / "core" / "file.py").resolve()

    def test_skips_products_missing_from_installer_root(self, tmp_path: Path) -> None:
        rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)
        wa = _build(tmp_path, products=[Path("missing")], rules=[rule])

        wa.install()

        assert not (tmp_path / "work" / "core").exists()

    def test_symlinks_declared_products(self, tmp_path: Path) -> None:
        wa = _build(tmp_path, products=[Path("productA")])

        wa.install()

        link = tmp_path / "work" / "products" / "productA"
        assert link.is_symlink()


class TestUpdate:
    def test_dispatches_to_updater_matching_update_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wa = _build(tmp_path, update_mode=UpdaterName.STRICT)
        updater = MagicMock()
        add_updater = MagicMock(return_value=updater)
        monkeypatch.setattr(
            "installable.workarea_installable.add_updater", add_updater
        )

        wa.update()

        add_updater.assert_called_once_with(name=UpdaterName.STRICT.value, workarea=wa)
        updater.assert_called_once_with()

    def test_smooth_mode_reinstalls_without_clearing(self, tmp_path: Path) -> None:
        product_dir = tmp_path / "installer" / "productA"
        (product_dir / "core").mkdir(parents=True)
        (product_dir / "core" / "file.py").write_text("data")
        rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)
        wa = _build(
            tmp_path,
            products=[Path("productA")],
            rules=[rule],
            update_mode=UpdaterName.SMOOTH,
        )
        wa.install()
        stray = tmp_path / "work" / "stray.txt"
        stray.write_text("kept")

        wa.update()

        assert stray.exists()
        assert (tmp_path / "work" / "core" / "file.py").is_symlink()

    def test_strict_mode_clears_work_root_before_reinstalling(
        self, tmp_path: Path
    ) -> None:
        product_dir = tmp_path / "installer" / "productA"
        (product_dir / "core").mkdir(parents=True)
        (product_dir / "core" / "file.py").write_text("data")
        rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)
        wa = _build(
            tmp_path,
            products=[Path("productA")],
            rules=[rule],
            update_mode=UpdaterName.STRICT,
        )
        wa.install()
        stray = tmp_path / "work" / "stray.txt"
        stray.write_text("removed")

        wa.update()

        assert not stray.exists()
        assert (tmp_path / "work" / "core" / "file.py").is_symlink()


class TestRepair:
    def test_uses_repair_updater_regardless_of_update_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wa = _build(tmp_path, update_mode=UpdaterName.SMOOTH)
        updater = MagicMock()
        add_updater = MagicMock(return_value=updater)
        monkeypatch.setattr(
            "installable.workarea_installable.add_updater", add_updater
        )

        wa.repair()

        add_updater.assert_called_once_with(name=UpdaterName.REPAIR.value, workarea=wa)
        updater.assert_called_once_with()

    def test_removes_broken_links_then_reinstalls(self, tmp_path: Path) -> None:
        product_dir = tmp_path / "installer" / "productA"
        (product_dir / "core").mkdir(parents=True)
        (product_dir / "core" / "file.py").write_text("data")
        rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)
        wa = _build(
            tmp_path,
            products=[Path("productA")],
            rules=[rule],
        )
        wa.install()
        broken = tmp_path / "work" / "broken_link"
        broken.symlink_to(tmp_path / "work" / "does_not_exist")

        wa.repair()

        assert not broken.exists()
        assert (tmp_path / "work" / "core" / "file.py").is_symlink()


class TestClear:
    def test_removes_files_symlinks_and_directories(self, tmp_path: Path) -> None:
        wa = _build(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        (work_root / "file.txt").write_text("data")
        (work_root / "a_dir").mkdir()
        (work_root / "a_dir" / "nested.txt").write_text("nested")
        target = tmp_path / "link_target.txt"
        target.write_text("target")
        (work_root / "link").symlink_to(target)

        wa.clear()

        assert work_root.exists()
        assert list(work_root.iterdir()) == []
        assert target.exists()  # symlink target itself is untouched


class TestRepairBrokenLinks:
    def test_removes_only_broken_symlinks(self, tmp_path: Path) -> None:
        wa = _build(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        valid_target = work_root / "target.txt"
        valid_target.write_text("data")
        valid_link = work_root / "valid_link"
        valid_link.symlink_to(valid_target)
        broken_link = work_root / "broken_link"
        broken_link.symlink_to(work_root / "missing")
        regular_file = work_root / "regular.txt"
        regular_file.write_text("data")

        wa.repair_broken_links()

        assert not broken_link.exists()
        assert valid_link.is_symlink()
        assert regular_file.exists()

    def test_interactive_keeps_link_on_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wa = _build(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken_link = work_root / "broken_link"
        broken_link.symlink_to(work_root / "missing")
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")

        wa.repair_broken_links(interactive=True)

        assert broken_link.is_symlink()

    def test_interactive_removes_link_on_confirmation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wa = _build(tmp_path)
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken_link = work_root / "broken_link"
        broken_link.symlink_to(work_root / "missing")
        monkeypatch.setattr("builtins.input", lambda _prompt: "y")

        wa.repair_broken_links(interactive=True)

        assert not broken_link.exists()


class TestRuntimeEnvironment:
    def test_pythonpath_joins_resolved_runtime_paths(self, tmp_path: Path) -> None:
        wa = _build(tmp_path)

        expected = os.pathsep.join(
            [
                str((tmp_path / "work" / "core" / "python").resolve()),
                str((tmp_path / "work" / "rest").resolve()),
            ]
        )
        assert wa.pythonpath() == expected

    def test_assert_runtime_ready_raises_when_paths_missing(
        self, tmp_path: Path
    ) -> None:
        wa = _build(tmp_path)

        with pytest.raises(FileNotFoundError):
            wa.runtime_env()

    def test_runtime_env_returns_environ_copy_with_pythonpath(
        self, tmp_path: Path
    ) -> None:
        wa = _build(tmp_path)
        (tmp_path / "work" / "core" / "python").mkdir(parents=True)
        (tmp_path / "work" / "rest").mkdir(parents=True)

        env = wa.runtime_env()

        assert env["PYTHONPATH"] == wa.pythonpath()
        assert env["PATH"] == os.environ["PATH"]


class TestUnimplementedInstallableBaseMethods:
    def test_download_raises(self, tmp_path: Path) -> None:
        wa = _build(tmp_path)

        with pytest.raises(NotImplementedError):
            wa.download(tmp_path)


def test_default_update_mode_is_smooth(tmp_path: Path) -> None:
    wa = WorkareaInstallable(
        workarea=Workarea(
            installer_root=tmp_path / "installer",
            work_root=tmp_path / "work",
            products=[],
        )
    )

    assert wa.update_mode == UpdaterName.SMOOTH
