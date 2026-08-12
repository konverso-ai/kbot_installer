"""Resolve 3rdparty environment (PG_DIR, LD_LIBRARY_PATH) from ``versions.env``.

The kbot ``3rdparty`` product ships a ``versions.env`` file that ``kbot``'s
shell ``env.sh`` sources to expose variables such as ``PG_DIR`` and to build
``LD_LIBRARY_PATH``. ``kbot-installer`` cannot rely on ``env.sh`` (it runs in
its own isolated interpreter, before ``kbot`` is even downloaded), so this
module reproduces the small subset it needs by parsing ``versions.env``
directly, once the product has been downloaded under the installer directory.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Order of library directories mirrors ``kbot/bin/env.sh``'s LD_LIBRARY_PATH so
# the internal PostgreSQL binaries (pg_ctl/initdb) resolve their 3rdparty
# shared libraries the same way. Each entry is a (versions.env var, subdir).
_LD_LIBRARY_ENTRIES: tuple[tuple[str, str], ...] = (
    ("PYTHON_DIR", "lib"),
    ("PG_DIR", "lib"),
    ("SSL_DIR", "lib64"),
    ("SSL_DIR", "lib"),
    ("ZLIB_DIR", "lib"),
    ("BZIP2_DIR", "lib"),
    ("PCRE2_DIR", "lib"),
    ("HTTPD_DIR", "lib"),
    ("CURL_DIR", "lib"),
    ("NGHTTP2_DIR", "lib64"),
    ("NGHTTP2_DIR", "lib"),
    ("LIBEVENT_DIR", "lib"),
    ("FILE_DIR", "lib"),
)

_VAR_REF = re.compile(r"\$\{(\w+)\}|\$(\w+)")
_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_env_file(path: Path, base_vars: dict[str, str] | None = None) -> dict[str, str]:
    """Parse a bash-style ``VAR=value`` env file with ``${VAR}`` substitution.

    Only the small feature set used by ``versions.env`` is supported: simple
    ``VAR=value`` assignments, ``${OTHER}`` / ``$OTHER`` references resolved
    against ``base_vars`` and previously parsed values, ``#`` comments and
    blank lines. Values are not shell-unquoted beyond stripping surrounding
    single or double quotes.

    Args:
        path: Path to the env file to parse.
        base_vars: Externally provided variables (e.g. ``THIRDPARTY_HOME``)
            made available for substitution.

    Returns:
        A mapping of every assigned variable to its resolved value. The
        provided ``base_vars`` are not included in the result.

    """
    resolved: dict[str, str] = dict(base_vars or {})
    assigned: dict[str, str] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _ASSIGNMENT.match(line)
        if not match:
            continue

        name, raw_value = match.group(1), match.group(2).strip()
        if (raw_value.startswith('"') and raw_value.endswith('"')) or (
            raw_value.startswith("'") and raw_value.endswith("'")
        ):
            raw_value = raw_value[1:-1]

        value = _substitute(raw_value, resolved)
        resolved[name] = value
        assigned[name] = value

    return assigned


def _substitute(value: str, variables: dict[str, str]) -> str:
    """Replace ``${VAR}``/``$VAR`` references using ``variables`` (empty if unknown)."""

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        return variables.get(name, "")

    return _VAR_REF.sub(_replace, value)


def _thirdparty_dir(installer_path: Path) -> Path:
    """Return the ``3rdparty`` product directory inside the installer directory."""
    return installer_path / "3rdparty"


def _load_versions(installer_path: Path) -> dict[str, str] | None:
    """Parse ``<installer>/3rdparty/versions.env`` or return None if absent."""
    thirdparty = _thirdparty_dir(installer_path)
    versions_env = thirdparty / "versions.env"
    if not versions_env.is_file():
        return None
    return parse_env_file(versions_env, {"THIRDPARTY_HOME": str(thirdparty)})


def resolve_pg_dir(installer_path: Path) -> Path | None:
    """Resolve ``PG_DIR`` from ``<installer>/3rdparty/versions.env``.

    Args:
        installer_path: Installer directory holding the downloaded products.

    Returns:
        The resolved ``PG_DIR`` as a ``Path``, or ``None`` when the
        ``versions.env`` file is missing or does not define ``PG_DIR``.

    """
    variables = _load_versions(installer_path)
    if not variables:
        return None
    pg_dir = variables.get("PG_DIR")
    return Path(pg_dir) if pg_dir else None


def thirdparty_ld_library_path(installer_path: Path) -> str | None:
    """Build the ``LD_LIBRARY_PATH`` value for the 3rdparty shared libraries.

    Mirrors the ordering used by ``kbot/bin/env.sh`` so the internal
    PostgreSQL binaries load the right libraries, keeping only directories that
    actually exist on disk.

    Args:
        installer_path: Installer directory holding the downloaded products.

    Returns:
        An ``os.pathsep``-joined string of existing 3rdparty library
        directories, or ``None`` when ``versions.env`` is missing or no
        directory could be resolved.

    """
    variables = _load_versions(installer_path)
    if not variables:
        return None

    entries: list[str] = []
    for var_name, subdir in _LD_LIBRARY_ENTRIES:
        base = variables.get(var_name)
        if not base:
            continue
        candidate = Path(base) / subdir
        candidate_str = str(candidate)
        if candidate.is_dir() and candidate_str not in entries:
            entries.append(candidate_str)

    if not entries:
        return None
    return ":".join(entries)


def resolve_pg_dir_str(installer_path: Path) -> str | None:
    """Resolve ``PG_DIR`` from the downloaded 3rdparty ``versions.env`` as a string.

    Args:
        installer_path: Installer directory holding the downloaded products.

    Returns:
        The resolved ``PG_DIR`` path as a string, or None when it cannot be found.

    """
    pg_dir = resolve_pg_dir(installer_path)
    return str(pg_dir) if pg_dir is not None else None


def prepend_thirdparty_ld_library_path(installer_path: Path) -> None:
    """Prepend the 3rdparty library directories to ``LD_LIBRARY_PATH``.

    The internal PostgreSQL binaries (pg_ctl/initdb) are launched via
    ``subprocess`` without an explicit environment, so they inherit
    ``os.environ``. Prepending the 3rdparty library directories mirrors what
    ``kbot/bin/env.sh`` does and lets those binaries resolve their shared
    libraries regardless of the install location. The operation is idempotent.

    Args:
        installer_path: Installer directory holding the downloaded products.

    """
    thirdparty_path = thirdparty_ld_library_path(installer_path)
    if not thirdparty_path:
        return

    current = os.environ.get("LD_LIBRARY_PATH", "")
    existing = current.split(os.pathsep) if current else []
    new_entries = [entry for entry in thirdparty_path.split(os.pathsep) if entry not in existing]
    if not new_entries:
        return

    combined = new_entries + existing
    os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(filter(None, combined))
