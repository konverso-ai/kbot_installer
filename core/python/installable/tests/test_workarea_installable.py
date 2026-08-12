"""Tests for WorkareaInstallable."""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from installable.workarea_installable import WorkareaInstallable
from workarea.rule_action import RuleAction
from workarea.workarea import Workarea
from workarea.workarea_rule import WorkareaRule


def _build(
    tmp_path: Path,
    *,
    products: list[Path] | None = None,
    rules: list[WorkareaRule] | None = None,
    update_mode: bool = False,
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
        product_dir = tmp_path / "installer" / "productA"
        product_dir.mkdir(parents=True)
        wa = _build(tmp_path, products=[Path("productA")])

        wa.install()

        link = tmp_path / "work" / "products" / "productA"
        assert link.is_symlink()
        assert link.resolve() == product_dir.resolve()

    def test_passes_resolved_product_roots_to_tests_dir_cleanup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: cleanup_unused_tests_dir must receive full product roots.

        Passing bare product names (relative to the CWD, not to installer_root)
        makes the "is the tests dir used by a product" check always negative and
        can lead to attempting to remove a non-existent directory.
        """
        product_dir = tmp_path / "installer" / "productA"
        (product_dir / "tests").mkdir(parents=True)
        wa = _build(tmp_path, products=[Path("productA")])

        cleanup_mock = MagicMock()
        monkeypatch.setattr(
            "installable.workarea_installable.cleanup_unused_tests_dir", cleanup_mock
        )

        wa.install()

        cleanup_mock.assert_called_once_with(
            tmp_path / "work", [product_dir], interactive=False
        )

    def test_interactive_update_mode_is_forwarded_to_tests_dir_cleanup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wa = _build(tmp_path, update_mode=True)
        cleanup_mock = MagicMock()
        monkeypatch.setattr(
            "installable.workarea_installable.cleanup_unused_tests_dir", cleanup_mock
        )

        wa.install()

        cleanup_mock.assert_called_once_with(tmp_path / "work", [], interactive=True)


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

    def test_assert_runtime_ready_raises_when_paths_missing(self, tmp_path: Path) -> None:
        wa = _build(tmp_path)

        with pytest.raises(FileNotFoundError):
            wa.runtime_env()

    def test_runtime_env_returns_environ_copy_with_pythonpath(self, tmp_path: Path) -> None:
        wa = _build(tmp_path)
        (tmp_path / "work" / "core" / "python").mkdir(parents=True)
        (tmp_path / "work" / "rest").mkdir(parents=True)

        env = wa.runtime_env()

        assert env["PYTHONPATH"] == wa.pythonpath()
        assert env["PATH"] == os.environ["PATH"]


def test_default_update_mode_is_false(tmp_path: Path) -> None:
    wa = WorkareaInstallable(
        workarea=Workarea(
            installer_root=tmp_path / "installer",
            work_root=tmp_path / "work",
            products=[],
        )
    )

    assert wa.update_mode is False

