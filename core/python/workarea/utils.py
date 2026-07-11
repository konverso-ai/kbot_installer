import shutil
from collections.abc import Iterable
from fnmatch import fnmatch
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from workarea.rule_action import RuleAction
from workarea.workarea_rule import WorkareaRule

if TYPE_CHECKING:
    from workarea.workarea_rule import WorkAreaRule


def should_keep(path: Path, root: Path, rule: "WorkAreaRule") -> bool:
    relative = path.relative_to(root).as_posix()

    if rule.includes:
        if not any(fnmatch(relative, pattern) for pattern in rule.includes):
            return False

    if rule.excludes:
        if any(fnmatch(relative, pattern) for pattern in rule.excludes):
            return False

    return True


def render_variables(content: str, variables: dict[str, str]) -> str:
    for key, value in variables.items():
        content = content.replace(key, value)
    return content


def is_broken_symlink(path: Path) -> bool:
    return path.is_symlink() and not path.exists()


def link_source(source: Path, target: Path) -> None:
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)


def copy_source(
    source: Path,
    target: Path,
    *,
    variables: dict[str, str] | None = None,
) -> None:
    variables = variables or {}

    target.parent.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if variables:
        content = source.read_text(encoding="utf-8")
        content = render_variables(content, variables)
        target.write_text(content, encoding="utf-8")
        shutil.copymode(source, target)
        return

    shutil.copy2(source, target)


def iter_sources(root: Path, rule: "WorkAreaRule"):
    candidates = root.rglob("*") if rule.recursive else root.iterdir()

    for path in candidates:
        if should_keep(path, root, rule):
            yield path


def apply_rule(
    product_root: Path,
    work_root: Path,
    rule: WorkareaRule,
    *,
    runtime_variables: dict[str, str],
) -> None:
    source_root = product_root / rule.source

    if not source_root.exists():
        return

    target_root = work_root / rule.target_path()

    variables = {name: runtime_variables[name] for name in rule.placeholders}

    for source in iter_sources(source_root, rule):
        relative = source.relative_to(source_root)
        target = target_root / relative

        if target.exists() or target.is_symlink():
            continue

        match rule.action:
            case RuleAction.LINK:
                link_source(source, target)
            case RuleAction.COPY:
                copy_source(source, target, variables=variables)


def apply_rules(
    product_root: Path,
    work_root: Path,
    rules: list["WorkAreaRule"],
    *,
    runtime_variables: dict[str, str],
) -> None:
    for rule in rules:
        apply_rule(
            product_root=product_root,
            work_root=work_root,
            rule=rule,
            runtime_variables=runtime_variables,
        )


def setup_kbot_conf(work_root: Path) -> None:
    path = work_root / "conf" / "kbot.conf"
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        return

    path.write_text(
        "# Kbot configuration file\n"
        "\n# If possible, prefer saving in Site or Customer level configuation file"
    )


def setup_runtime_dirs(work_root: Path) -> None:
    for path in [
        work_root / "logs" / "httpd",
        work_root / "var" / "pkl",
        work_root / "var" / "pkl" / "storage",
        work_root / "var" / "pkl" / "test_results",
        work_root / "var" / "cache",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def setup_products(work_root: Path, products: Iterable[Path]) -> None:
    products_root = work_root / "products"
    products_root.mkdir(parents=True, exist_ok=True)

    for product_root in products:
        target = products_root / product_root.name

        if target.exists() or target.is_symlink():
            continue

        target.symlink_to(product_root)


def setup_drf_yasg_static(work_root: Path) -> None:
    source = Path(str(files("drf_yasg") / "static"))
    target = work_root / "ui" / "web" / "static"

    if not source.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() or target.is_symlink():
        return

    target.symlink_to(source)


def cleanup_unused_tests_dir(
    work_root: Path, products_root: Iterable[Path], *, interactive: bool
) -> None:
    tests_dir = work_root / "tests"

    if any((product_root / "tests").exists() for product_root in products_root):
        return

    if interactive:
        answer = input(f"Not used directory 'tests' ({tests_dir}). Remove it? [Y/n] ")
        if answer not in {"y", "yes"}:
            return

    shutil.rmtree(tests_dir)
