from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import tomlkit
from tomlkit.items import AoT

try:
    from packaging.requirements import Requirement
    from packaging.version import InvalidVersion
    from packaging.version import parse as parse_version
except Exception:  # pragma: no cover
    Requirement = None  # type: ignore
    InvalidVersion = Exception  # type: ignore
    parse_version = None  # type: ignore


@dataclass
class Conflict:
    path: str
    current_repr: str
    incoming_repr: str
    reason: str


def _dumps_value_as_toml(v: Any) -> str:
    doc = tomlkit.document()
    doc.add("x", v)
    s = tomlkit.dumps(doc)
    return s.split("=", 1)[1].strip()


def _norm_req_name(req_str: str) -> tuple[str, str]:
    raw = req_str.strip()
    if Requirement is None:
        name = raw.split()[0]
        name = name.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].split("!=")[0]
        norm = name.lower().replace("_", "-")
        return norm, raw

    r = Requirement(raw)
    norm = r.name.lower().replace("_", "-")
    return norm, raw


def _req_map(reqs: list[str]) -> dict[str, str]:
    m: dict[str, str] = {}
    for s in reqs:
        k, canon = _norm_req_name(s)
        m[k] = canon
    return m


def _dominant_version_token(req_str: str) -> Any:
    """Single comparable value for 'how new' a specifier is (best effort)."""
    if parse_version is None or Requirement is None:
        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", req_str)
        if m:
            try:
                return tuple(int(x) for x in m.group(1).split("."))
            except ValueError:
                pass
        return (0,)

    try:
        req = Requirement(req_str.strip())
    except Exception:
        return (0,)

    pin: Any = None
    lower: Any = None
    for sp in req.specifier:
        try:
            v = parse_version(sp.version)
        except (InvalidVersion, TypeError, ValueError):
            continue
        if sp.operator == "==":
            pin = v if pin is None else max(pin, v)
        elif sp.operator in (">=", "~=", ">"):
            lower = v if lower is None else max(lower, v)

    if pin is not None:
        return (2, pin)
    if lower is not None:
        return (1, lower)
    return (0, parse_version("0"))


def _pick_newer_requirement(cur: str, inc: str) -> str:
    """Return the requirement string that is newer (more recent pin/range)."""
    rc, ri = _dominant_version_token(cur), _dominant_version_token(inc)
    if rc == ri:
        return cur
    if rc > ri:
        return cur
    return inc


def _get_deps(doc: Any) -> list[str]:
    try:
        proj = doc.get("project", None)
        if proj is None:
            return []
        deps = proj.get("dependencies", None)
        if deps is None:
            return []
        return list(deps)
    except Exception:
        return []


def _deps_array_is_multiline(deps_item: Any) -> bool:
    if deps_item is None:
        return False
    try:
        if hasattr(deps_item, "as_string"):
            return "\n" in deps_item.as_string()
    except Exception:
        pass
    return False


def _pick_deps_multiline_style(*docs: Any) -> bool:
    for doc in docs:
        try:
            proj = doc.get("project")
            if proj is None:
                continue
            deps = proj.get("dependencies")
            if deps is not None and _deps_array_is_multiline(deps):
                return True
        except Exception:
            pass
    return False


def _set_deps(doc: Any, deps: list[str], multiline: bool) -> None:
    if "project" not in doc:
        doc["project"] = tomlkit.table()
    arr = tomlkit.array()
    arr.multiline(multiline)
    for d in deps:
        arr.append(d)
    doc["project"]["dependencies"] = arr


def _merge_dependencies(
    base_doc: Any,
    current_doc: Any,
    incoming_doc: Any,
) -> None:
    """Merge dependency entries: always pick the newer specifier when both sides define a package."""
    base_list = _get_deps(base_doc)
    cur_list = _get_deps(current_doc)
    inc_list = _get_deps(incoming_doc)

    if not base_list and not cur_list and not inc_list:
        return

    base = _req_map(base_list)
    cur = _req_map(cur_list)
    inc = _req_map(inc_list)

    all_keys = set(base) | set(cur) | set(inc)
    out: dict[str, str] = {}

    for k in sorted(all_keys):
        cur_s = cur.get(k)
        inc_s = inc.get(k)
        base_s = base.get(k)

        if cur_s is None and inc_s is None:
            continue

        if cur_s is not None and inc_s is None:
            # Incoming removed this package
            if base_s is not None and cur_s == base_s:
                # Current did not change the dep vs base: accept removal
                continue
            # Current modified the dep: keep current's specifier
            out[k] = cur_s
            continue

        if cur_s is None and inc_s is not None:
            # Current removed this package
            if base_s is not None and inc_s == base_s:
                # Incoming did not change the dep vs base: accept current's removal
                continue
            # Incoming added or changed the dep: take incoming's specifier
            out[k] = inc_s
            continue

        # Both have a specifier
        assert cur_s is not None and inc_s is not None
        if cur_s == inc_s:
            out[k] = cur_s
        else:
            out[k] = _pick_newer_requirement(cur_s, inc_s)

    ordered: list[str] = []
    seen = set()
    for s in cur_list:
        nk, _ = _norm_req_name(s)
        if nk in out and nk not in seen:
            ordered.append(out[nk])
            seen.add(nk)
    for k in sorted(out.keys()):
        if k not in seen:
            ordered.append(out[k])
            seen.add(k)

    _set_deps(
        current_doc,
        ordered,
        _pick_deps_multiline_style(current_doc, incoming_doc, base_doc),
    )


def _toml_get(doc: Any, path: list[str]) -> Any:
    cur = doc
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _toml_set(doc: Any, path: list[str], value: Any) -> None:
    cur = doc
    for p in path[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = tomlkit.table()
        cur = cur[p]
    cur[path[-1]] = value


def _iter_paths(obj: Any, prefix: list[str] | None = None):
    prefix = prefix or []
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_paths(v, prefix + [str(k)])
    else:
        yield prefix


def _is_version_path(path: list[str]) -> bool:
    return path == ["project", "version"]


def _is_dependencies_path(path: list[str]) -> bool:
    return path == ["project", "dependencies"]


def _is_tool_uv_sources_path(path: list[str]) -> bool:
    return len(path) >= 3 and path[0] == "tool" and path[1] == "uv" and path[2] == "sources"


def _is_tool_uv_index_path(path: list[str]) -> bool:
    return path == ["tool", "uv", "index"]


def _get_tool_uv(doc: Any) -> Any:
    try:
        t = doc.get("tool")
        if t is None:
            return None
        return t.get("uv")
    except Exception:
        return None


def _merge_tool_uv_sources(cur_doc: Any, inc_doc: Any) -> None:
    """
    Union-merge [tool.uv.sources]: keys from current ∪ incoming.
    If both define the same key with different values, incoming wins.
    """
    cur_uv = _get_tool_uv(cur_doc)
    inc_uv = _get_tool_uv(inc_doc)
    cur_src = cur_uv.get("sources") if cur_uv is not None else None
    inc_src = inc_uv.get("sources") if inc_uv is not None else None

    if cur_src is None and inc_src is None:
        return

    keys: set[str] = set()
    if cur_src is not None:
        keys |= set(cur_src.keys())
    if inc_src is not None:
        keys |= set(inc_src.keys())

    out = tomlkit.table()
    for k in sorted(keys):
        vc = cur_src.get(k) if cur_src is not None else None
        vi = inc_src.get(k) if inc_src is not None else None
        if vc is None and vi is None:
            continue
        if vc is None:
            out[k] = vi
        elif vi is None:
            out[k] = vc
        elif vc == vi:
            out[k] = vc
        else:
            out[k] = vi

    if "tool" not in cur_doc:
        cur_doc["tool"] = tomlkit.table()
    if "uv" not in cur_doc["tool"]:
        cur_doc["tool"]["uv"] = tomlkit.table()
    if len(out) == 0:
        uv = cur_doc["tool"]["uv"]
        if isinstance(uv, dict) and "sources" in uv:
            del uv["sources"]
    else:
        cur_doc["tool"]["uv"]["sources"] = out


def _merge_tool_uv_index(cur_doc: Any, inc_doc: Any) -> None:
    """
    Union-merge [[tool.uv.index]] by table ``name``: entries from current, then
    any names only on incoming; same ``name`` with different fields → incoming wins.
    """
    cur_uv = _get_tool_uv(cur_doc)
    inc_uv = _get_tool_uv(inc_doc)
    cur_idx = cur_uv.get("index") if cur_uv is not None else None
    inc_idx = inc_uv.get("index") if inc_uv is not None else None

    if cur_idx is None and inc_idx is None:
        return

    cur_list = list(cur_idx) if cur_idx is not None else []
    inc_list = list(inc_idx) if inc_idx is not None else []

    by_name: dict[str, Any] = {}
    order: list[str] = []
    for e in cur_list:
        n = e.get("name")
        if n is None:
            continue
        nk = str(n)
        if nk not in by_name:
            by_name[nk] = e
            order.append(nk)
        else:
            by_name[nk] = e
    for e in inc_list:
        n = e.get("name")
        if n is None:
            continue
        nk = str(n)
        if nk not in by_name:
            by_name[nk] = e
            order.append(nk)
        elif e != by_name[nk]:
            by_name[nk] = e

    new_aot = AoT([])
    for nk in order:
        new_aot.append(by_name[nk])

    if "tool" not in cur_doc:
        cur_doc["tool"] = tomlkit.table()
    if "uv" not in cur_doc["tool"]:
        cur_doc["tool"]["uv"] = tomlkit.table()
    if len(new_aot) == 0:
        uv = cur_doc["tool"]["uv"]
        if isinstance(uv, dict) and "index" in uv:
            del uv["index"]
    else:
        cur_doc["tool"]["uv"]["index"] = new_aot


def merge(base: str, current: str, incoming: str) -> str:
    """
    Merge driver entrypoint.
    - ``project.version``: always taken from *current*.
    - ``project.dependencies``: per-package, keep the newer specifier (pin/range).
    - ``[tool.uv.sources]``: union of keys from current and incoming (incoming wins on same key).
    - ``[[tool.uv.index]]``: union of index tables by ``name`` (incoming wins on same name).
    - All other keys: classic 3-way merge (incoming if current unchanged vs base, else conflict).
    """
    base_doc = tomlkit.parse(base) if base.strip() else tomlkit.document()
    cur_doc = tomlkit.parse(current) if current.strip() else tomlkit.document()
    inc_doc = tomlkit.parse(incoming) if incoming.strip() else tomlkit.document()

    version_current = _toml_get(cur_doc, ["project", "version"])

    conflicts: list[Conflict] = []

    base_paths = set(tuple(p) for p in _iter_paths(base_doc))
    cur_paths = set(tuple(p) for p in _iter_paths(cur_doc))
    inc_paths = set(tuple(p) for p in _iter_paths(inc_doc))
    all_paths = base_paths | cur_paths | inc_paths

    for tpath in sorted(all_paths):
        path = list(tpath)
        if (
            not path
            or _is_version_path(path)
            or _is_dependencies_path(path)
            or _is_tool_uv_sources_path(path)
            or _is_tool_uv_index_path(path)
        ):
            continue

        b = _toml_get(base_doc, path)
        c = _toml_get(cur_doc, path)
        i = _toml_get(inc_doc, path)

        if i is None and b is None:
            continue

        if c == b and i != b:
            _toml_set(cur_doc, path, i)
        elif i == b:
            continue
        else:
            if c != i:
                conflicts.append(
                    Conflict(
                        path=".".join(path),
                        current_repr=_dumps_value_as_toml(c),
                        incoming_repr=_dumps_value_as_toml(i),
                        reason="Concurrent changes (3-way).",
                    )
                )

    _merge_dependencies(base_doc, cur_doc, inc_doc)
    _merge_tool_uv_sources(cur_doc, inc_doc)
    _merge_tool_uv_index(cur_doc, inc_doc)

    if version_current is not None:
        if "project" not in cur_doc:
            cur_doc["project"] = tomlkit.table()
        cur_doc["project"]["version"] = version_current

    merged = tomlkit.dumps(cur_doc).rstrip() + "\n"

    if conflicts:
        merged += "\n# ===== MERGE CONFLICTS (manual resolution required) =====\n"
        for idx, cf in enumerate(conflicts, 1):
            merged += f"# [{idx}] Path: {cf.path}\n"
            merged += f"# Reason: {cf.reason}\n"
            merged += "<<<<<<< CURRENT\n"
            merged += f"{cf.current_repr}\n"
            merged += "=======\n"
            merged += f"{cf.incoming_repr}\n"
            merged += ">>>>>>> INCOMING\n"

    return merged
