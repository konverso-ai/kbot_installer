"""Filesystem helpers for laying out and maintaining a product workarea."""

import getpass
import json
import shutil
from collections.abc import Iterable, Iterator
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any

from installer_support.thirdparty_env import resolve_site_packages_dir
from interactivity.base import InteractivePrompter
from utils.Logger import logger
from utils.product.product import Product
from workarea.rule_action import RuleAction
from workarea.workarea_rule import WorkareaRule

if TYPE_CHECKING:
    from workarea.workarea_rule import WorkAreaRule

log = logger.get_package_logger("workarea")


def _matches_glob(relative_parts: tuple[str, ...], pattern_parts: tuple[str, ...]) -> bool:
    """Recursively match path segments against glob pattern segments.

    Unlike `fnmatch`, a `**` pattern segment matches zero or more whole path
    segments (as in `.gitignore`/glob conventions), so `**/*.py` matches both
    top-level files (e.g. `Bot.py`) and nested ones (e.g. `sub/Bot.py`). Every
    other pattern segment is matched against a single path segment via
    `fnmatch` (so `*`, `?`, and `[...]` still apply within a segment, but
    never cross a `/`).

    Args:
        relative_parts: Path segments (as returned by splitting a POSIX
            relative path on `/`) to match.
        pattern_parts: Glob pattern segments to match against.

    Returns:
        True if `relative_parts` fully matches `pattern_parts`.

    """
    if not pattern_parts:
        return not relative_parts

    head, *rest_pattern = pattern_parts

    if head == "**":
        return _matches_glob(relative_parts, tuple(rest_pattern)) or (
            bool(relative_parts) and _matches_glob(relative_parts[1:], pattern_parts)
        )

    if not relative_parts:
        return False

    return fnmatch(relative_parts[0], head) and _matches_glob(relative_parts[1:], tuple(rest_pattern))


def matches_pattern(relative: str, pattern: str) -> bool:
    """Check whether a POSIX relative path matches a glob pattern.

    Args:
        relative: POSIX-style relative path (e.g. `"core/python/Bot.py"`).
        pattern: Glob pattern, where `**` matches zero or more whole path
            segments (e.g. `"**/*.py"`), unlike plain `fnmatch` patterns.

    Returns:
        True if `relative` matches `pattern`.

    """
    return _matches_glob(tuple(relative.split("/")), tuple(pattern.split("/")))


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

    if rule.includes and not any(matches_pattern(relative, pattern) for pattern in rule.includes):
        return False

    return not (rule.excludes and any(matches_pattern(relative, pattern) for pattern in rule.excludes))


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


def repair_broken_links(paths: Iterable[Path], *, interactive: bool = False) -> None:
    """Find and remove broken symlinks among a set of paths.

    Args:
        paths: Paths to check for broken symlinks (e.g. `work_root.rglob("*")`).
        interactive: If True, prompt for confirmation before removing each broken
            symlink (an empty answer means yes); otherwise remove them all without asking.

    """
    for path in paths:
        if not is_broken_symlink(path=path):
            continue

        if interactive and not InteractivePrompter().ask_yn(f"Broken symlink {path}. Rebuild it? [Y/n] "):
            continue

        path.unlink()


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
    the source's file mode preserved. Dangling symlinks (e.g. an absolute
    link to the build machine shipped in a product archive) are skipped.

    Args:
        source: Product source path to copy from.
        target: Workarea path to create.
        variables: Placeholder values to render into the file content. If
            None or empty, the file is copied byte-for-byte.

    """
    if source.is_symlink() and not source.exists():
        log.warning("Skipping dangling symlink '%s' -> '%s'.", source, source.readlink())
        return

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
        "# Kbot configuration file\n\n# If possible, prefer saving in Site or Customer level configuation file"
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


def _load_registry_entries(products: Iterable[Path]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for product_root in products:
        description_xml = product_root / "description.xml"
        if not description_xml.exists():
            continue

        product = Product.from_xml_file(description_xml)
        description_json = product_root / "description.json"
        if description_json.exists():
            product = Product.merge(product, Product.from_json_file(description_json))

        entry = product.to_json()
        entry["path"] = str(product_root.absolute())
        entry["description"] = str(description_xml.absolute())
        entries.setdefault(product.name, entry)
    return entries


def _order_registry_entries(entries: dict[str, dict[str, Any]]) -> list[str]:
    """Order product names children first, parents last.

    Depth-first post-order walk from each root product (one no other
    installed product depends on), reversed, as the legacy `utils/deps.py` did.

    Args:
        entries: Registry entries keyed by product name.

    Returns:
        Product names in pipeline order.

    Raises:
        ValueError: If the product dependencies are circular.

    """
    depended_on = {parent for entry in entries.values() for parent in entry["parents"]}
    roots = sorted(name for name in entries if name not in depended_on)
    if len(roots) > 1:
        log.warning("Several root products found: %s", ", ".join(roots))

    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in ordered:
            return
        if name in visiting:
            msg = f"Circular product dependency involving '{name}'"
            raise ValueError(msg)

        visiting.add(name)
        for parent in entries[name]["parents"]:
            if parent in entries:
                visit(parent)
            else:
                log.warning("Parent product '%s' of '%s' is not installed", parent, name)
        visiting.remove(name)
        ordered.append(name)

    # Unreachable products can only be part of a cycle; visiting them raises.
    for name in [*roots, *sorted(entries)]:
        visit(name)
    ordered.reverse()
    return ordered


def setup_products_registry(work_root: Path, products: Iterable[Path]) -> None:
    """Write `var/products.json`, the product pipeline read by kbot at runtime.

    kbot (`common.Product.ProductList.populate`, and `get_variable` in
    `bin/env.sh` through `tools/GetProducts.py`) walks this list in order, so
    the first product defining a file or a `kbot.env` variable wins: products
    are listed children first, parents last.

    The file is always rewritten, so an update picks up added or changed
    products. Product roots without a `description.xml` are ignored, as are
    declared parents that are not installed.

    Args:
        work_root: Root directory of the workarea.
        products: Installed product root directories.

    Raises:
        ValueError: If the product dependencies are circular.

    """
    entries = _load_registry_entries(products)
    ordered = _order_registry_entries(entries)

    path = work_root / "var" / "products.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([entries[name] for name in ordered], indent=4), encoding="utf-8")


def setup_drf_yasg_static(work_root: Path, installer_root: Path) -> None:
    """Symlink the `drf_yasg` package's static assets into the workarea.

    The source directory is resolved from the 3rdparty interpreter kbot
    actually runs against (via `installer_support.thirdparty_env`), not from
    whatever `drf_yasg` may be installed in kbot-installer's own environment,
    so the served assets always match the version kbot ships.

    Does nothing if the `drf_yasg` static directory cannot be found, or if a
    target already exists at `work_root / "ui" / "web" / "static"`.

    Args:
        work_root: Root directory of the workarea.
        installer_root: Installer directory holding the downloaded products.

    """
    _setup_thirdparty_static(work_root, installer_root, "drf_yasg")


def setup_drf_spectacular_static(work_root: Path, installer_root: Path) -> None:
    """Symlink the drf-spectacular static assets into the workarea.

    `drf_spectacular` itself ships no static files: the Swagger UI / Redoc
    assets live in the `drf_spectacular_sidecar` package. The source directory
    is resolved from the 3rdparty interpreter kbot actually runs against (via
    `installer_support.thirdparty_env`), not from whatever may be installed in
    kbot-installer's own environment, so the served assets always match the
    version kbot ships.

    Does nothing if the `drf_spectacular_sidecar` static directory cannot be
    found, or if a target already exists at `work_root / "ui" / "web" / "static"`.

    Args:
        work_root: Root directory of the workarea.
        installer_root: Installer directory holding the downloaded products.

    """
    _setup_thirdparty_static(work_root, installer_root, "drf_spectacular_sidecar")


def _setup_thirdparty_static(work_root: Path, installer_root: Path, package: str) -> None:
    """Symlink `package`'s static assets, as installed in the 3rdparty interpreter, into the workarea."""
    site_packages = resolve_site_packages_dir(installer_root)
    if site_packages is None:
        return

    source = site_packages / package / "static"
    target = work_root / "ui" / "web" / "static"

    if not source.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() or target.is_symlink():
        return

    target.symlink_to(source)


def cleanup_unused_tests_dir(work_root: Path, products_root: Iterable[Path], *, interactive: bool) -> None:
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

    if not tests_dir.exists():
        return

    if any((product_root / "tests").exists() for product_root in products_root):
        return

    if interactive and not InteractivePrompter().ask_yn(f"Not used directory 'tests' ({tests_dir}). Remove it? [Y/n] "):
        return

    shutil.rmtree(tests_dir)


def runtime_variables(work_root: Path) -> dict[str, str]:
    """Build the runtime placeholder variables available when laying out a workarea.

    Args:
        work_root: Root directory of the workarea.

    Returns:
        Mapping of placeholder key (e.g. `__KBOT_HOME__`) to its resolved value,
        available for rules whose `placeholders` reference them.

    """
    return {
        "__KBOT_HOME__": str(work_root.resolve()),
        "__KBOT_USER__": getpass.getuser(),
    }


def clear_workarea(work_root: Path) -> None:
    """Remove every file, symlink, and directory directly under the work root.

    Args:
        work_root: Root directory of the workarea.

    """
    for child in work_root.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)
