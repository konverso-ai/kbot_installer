"""Filesystem helpers for laying out and maintaining a product workarea."""

import shutil
from collections.abc import Iterable, Iterator
from fnmatch import fnmatch
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from workarea.rule_action import RuleAction
from workarea.workarea_rule import WorkareaRule

if TYPE_CHECKING:
    from workarea.workarea_rule import WorkAreaRule


def should_keep(path: Path, root: Path, rule: "WorkAreaRule") -> bool:
    """Determine whether a path matches a rule's include/exclude patterns.

    Args:
        path: Path to evaluate, expected to be located under `root`.
        root: Root directory `path` is made relative to before matching.
        rule: Rule providing the `includes`/`excludes` glob patterns.

    Returns:
        True if `path` matches at least one include pattern (or no include
        patterns are set) and does not match any exclude pattern.

    """
    relative = path.relative_to(root).as_posix()

    if rule.includes and not any(
        fnmatch(relative, pattern) for pattern in rule.includes
    ):
        return False

    return not (
        rule.excludes and any(fnmatch(relative, pattern) for pattern in rule.excludes)
    )


def render_variables(content: str, variables: dict[str, str]) -> str:
    """Replace placeholder keys with their values in a text content.

    Args:
        content: Text to render, containing literal placeholder keys.
        variables: Mapping of placeholder key to replacement value.

    Returns:
        The content with every occurrence of each key replaced by its value.

    """
    for key, value in variables.items():
        content = content.replace(key, value)
    return content


def is_broken_symlink(path: Path) -> bool:
    """Check whether a path is a symlink pointing to a nonexistent target.

    Args:
        path: Path to check.

    Returns:
        True if `path` is a symlink whose target does not exist.

    """
    return path.is_symlink() and not path.exists()


def link_source(source: Path, target: Path) -> None:
    """Link a product source path into the workarea.

    Directories are created directly (mirroring the directory structure so
    files can be linked underneath); files are symlinked to `source`.

    Args:
        source: Product source path to link from.
        target: Workarea path to create.

    """
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
    """Copy a product source path into the workarea.

    Directories are created directly. Files are copied verbatim unless
    `variables` is given, in which case the source is read as text, its
    placeholders are rendered, and the result is written to `target` with
    the source's file mode preserved.

    Args:
        source: Product source path to copy from.
        target: Workarea path to create.
        variables: Placeholder values to render into the file content. If
            None or empty, the file is copied byte-for-byte.

    """
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


def iter_sources(root: Path, rule: "WorkAreaRule") -> Iterator[Path]:
    """Yield the paths under a root that a rule should keep.

    Args:
        root: Directory to enumerate paths from.
        rule: Rule controlling recursion and include/exclude filtering.

    Yields:
        Paths under `root` that match `rule`'s include/exclude patterns.

    """
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
    """Apply a single layout rule from a product root into the workarea.

    Resolves the rule's source directory under `product_root`, then links or
    copies every matching source path into the corresponding location under
    `work_root`. Existing targets (including broken symlinks) are left
    untouched.

    Args:
        product_root: Root directory of the product providing the sources.
        work_root: Root directory of the workarea to write targets into.
        rule: Layout rule describing the source, target, and action to apply.
        runtime_variables: Available runtime variable values, used to resolve
            the subset named in `rule.placeholders`.

    """
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
    """Apply a list of layout rules from a product root into the workarea.

    Args:
        product_root: Root directory of the product providing the sources.
        work_root: Root directory of the workarea to write targets into.
        rules: Layout rules to apply, in order.
        runtime_variables: Available runtime variable values, used to resolve
            each rule's `placeholders`.

    """
    for rule in rules:
        apply_rule(
            product_root=product_root,
            work_root=work_root,
            rule=rule,
            runtime_variables=runtime_variables,
        )


def setup_kbot_conf(work_root: Path) -> None:
    """Create the workarea's default `conf/kbot.conf` if it does not exist.

    Args:
        work_root: Root directory of the workarea.

    """
    path = work_root / "conf" / "kbot.conf"
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        return

    path.write_text(
        "# Kbot configuration file\n"
        "\n# If possible, prefer saving in Site or Customer level configuation file"
    )


def setup_runtime_dirs(work_root: Path) -> None:
    """Create the workarea's runtime directories (logs, cache, pkl storage).

    Args:
        work_root: Root directory of the workarea.

    """
    for path in [
        work_root / "logs" / "httpd",
        work_root / "var" / "pkl",
        work_root / "var" / "pkl" / "storage",
        work_root / "var" / "pkl" / "test_results",
        work_root / "var" / "cache",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def setup_products(work_root: Path, products: Iterable[Path]) -> None:
    """Symlink each installed product root into the workarea's products dir.

    Existing targets (including broken symlinks) are left untouched.

    Args:
        work_root: Root directory of the workarea.
        products: Product root directories to symlink under
            `work_root / "products"`, named after each product root's
            directory name.

    """
    products_root = work_root / "products"
    products_root.mkdir(parents=True, exist_ok=True)

    for product_root in products:
        target = products_root / product_root.name

        if target.exists() or target.is_symlink():
            continue

        target.symlink_to(product_root)


def setup_drf_yasg_static(work_root: Path) -> None:
    """Symlink the `drf_yasg` package's static assets into the workarea.

    Does nothing if the `drf_yasg` static directory cannot be found, or if a
    target already exists at `work_root / "ui" / "web" / "static"`.

    Args:
        work_root: Root directory of the workarea.

    """
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
    """Remove the workarea's `tests` directory if no product uses it.

    If any product root has its own `tests` directory, the workarea's
    `tests` directory is left in place. Otherwise, it is removed, prompting
    for confirmation first when `interactive` is set.

    Args:
        work_root: Root directory of the workarea.
        products_root: Product root directories to check for a `tests`
            subdirectory.
        interactive: Whether to prompt for confirmation before removing the
            directory.

    """
    tests_dir = work_root / "tests"

    if any((product_root / "tests").exists() for product_root in products_root):
        return

    if interactive:
        answer = input(f"Not used directory 'tests' ({tests_dir}). Remove it? [Y/n] ")
        if answer not in {"y", "yes"}:
            return

    shutil.rmtree(tests_dir)
