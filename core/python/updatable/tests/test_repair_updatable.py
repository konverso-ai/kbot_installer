"""Tests for updatable.repair_updatable module."""

from pathlib import Path

from installable.workarea_installable import WorkareaInstallable
from updatable.factory import UpdatableName
from updatable.repair_updatable import RepairUpdatable
from updatable.workarea_updatable import WorkareaUpdatable
from workarea.rule_action import RuleAction
from workarea.workarea import Workarea
from workarea.workarea_rule import WorkareaRule


def _workarea(tmp_path: Path, products: list[Path] | None = None) -> Workarea:
    return Workarea(
        installer_root=tmp_path / "installer",
        work_root=tmp_path / "work",
        products=products or [],
        rules=[WorkareaRule(source=Path("core"), action=RuleAction.LINK)],
    )


def test_removes_installer_links_and_broken_links_but_keeps_the_rest(tmp_path: Path) -> None:
    """Valid links into the installer go too (even through a symlinked product); the rest stays."""
    git_copy = tmp_path / "git" / "kbot"
    git_copy.mkdir(parents=True)
    (git_copy / "mod.py").write_text("kbot")
    installer = tmp_path / "installer"
    installer.mkdir()
    (installer / "kbot").symlink_to(git_copy)
    external = tmp_path / "external.txt"
    external.write_text("external")
    work_root = tmp_path / "work"
    (work_root / "core").mkdir(parents=True)
    product_link = work_root / "core" / "mod.py"
    product_link.symlink_to(installer / "kbot" / "mod.py")
    relative_product_link = work_root / "core" / "relative.py"
    relative_product_link.symlink_to(Path("..") / ".." / "installer" / "kbot" / "mod.py")
    product_dir_link = work_root / "products"
    product_dir_link.symlink_to(installer / "kbot")
    external_link = work_root / "external_link"
    external_link.symlink_to(external)
    broken_link = work_root / "broken_link"
    broken_link.symlink_to(tmp_path / "missing")
    regular_file = work_root / "core" / "local.py"
    regular_file.write_text("local")

    RepairUpdatable(_workarea(tmp_path))()

    remaining = sorted(path.relative_to(work_root).as_posix() for path in work_root.rglob("*"))
    assert remaining == ["core", "core/local.py", "external_link"]
    assert external_link.is_symlink()
    assert (git_copy / "mod.py").read_text() == "kbot"


def test_relinks_a_path_now_provided_by_a_higher_priority_product(tmp_path: Path) -> None:
    """Regression: after an upgrade, a still-valid link must move to the product that now wins the path."""
    installer = tmp_path / "installer"
    (installer / "custo" / "core").mkdir(parents=True)
    (installer / "kbot" / "core").mkdir(parents=True)
    (installer / "kbot" / "core" / "mod.py").write_text("kbot")
    products = [Path("custo"), Path("kbot")]
    WorkareaInstallable(workarea=_workarea(tmp_path, products)).install()
    (installer / "custo" / "core" / "mod.py").write_text("custo")

    WorkareaUpdatable(installable=WorkareaInstallable(workarea=_workarea(tmp_path, products)), mode=UpdatableName.REPAIR)()

    assert (tmp_path / "work" / "core" / "mod.py").read_text() == "custo"
