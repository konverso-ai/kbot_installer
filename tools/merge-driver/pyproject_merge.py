from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import tomlkit

try:
    # Handy for properly parsing "snow >=2026.1,<2026.2"
    from packaging.requirements import Requirement
except Exception:  # pragma: no cover
    Requirement = None  # type: ignore


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
    # "x = <...>\n" -> "<...>"
    return s.split("=", 1)[1].strip()


def _norm_req_name(req_str: str) -> tuple[str, str]:
    """
    Return (normalized_name, canonical_req_str).
    - normalized_name: used for comparison (pep503-ish)
    - canonical_req_str: a clean version to re-emit (when packaging is available)
    """
    raw = req_str.strip()
    if Requirement is None:
        # Naive fallback: split on space / comparators
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


def _set_deps(doc: Any, deps: list[str]) -> None:
    if "project" not in doc:
        doc["project"] = tomlkit.table()
    doc["project"]["dependencies"] = deps


def _merge_dependencies(
    base_doc: Any,
    current_doc: Any,
    incoming_doc: Any,
    conflicts: list[Conflict],
) -> None:
    base_list = _get_deps(base_doc)
    cur_list = _get_deps(current_doc)
    inc_list = _get_deps(incoming_doc)

    if not base_list and not cur_list and not inc_list:
        return

    base = _req_map(base_list)
    cur = _req_map(cur_list)
    inc = _req_map(inc_list)

    # Detect additions/removals on the incoming side compared to base
    base_keys = set(base)
    inc_keys = set(inc)

    added = inc_keys - base_keys
    removed = base_keys - inc_keys

    # Additions: if absent from current -> add it (specifier from incoming, since current has nothing)
    for k in sorted(added):
        if k in cur:
            continue
        cur[k] = inc[k]

    # Removals: if current == base (for this pkg) -> remove it, otherwise conflict
    for k in sorted(removed):
        base_val = base.get(k)
        cur_val = cur.get(k)
        if cur_val is None:
            continue  # already removed by current
        if base_val == cur_val:
            del cur[k]
        else:
            conflicts.append(
                Conflict(
                    path="project.dependencies",
                    current_repr=cur_val,
                    incoming_repr="(removed)",
                    reason=f"Incoming removes '{k}' but current has modified it since base.",
                )
            )

    # Changes: incoming modifies an existing specifier vs base
    common = (base_keys & inc_keys)
    for k in sorted(common):
        base_val = base.get(k)
        inc_val = inc.get(k)
        if base_val == inc_val:
            continue  # no change on the incoming side

        # Incoming wants to change something; we keep current ranges
        cur_val = cur.get(k)
        if cur_val is None:
            # current removed it, incoming modifies -> conflict
            conflicts.append(
                Conflict(
                    path="project.dependencies",
                    current_repr="(removed)",
                    incoming_repr=inc_val or "",
                    reason=f"Incoming modifies '{k}' but current has removed it.",
                )
            )
            continue

        # If current stayed equal to base: OK, keep current (so base==current)
        # => this incoming "change" is not applied, but we can note it.
        if cur_val == base_val:
            # No change, keep current. Optional: no conflict.
            continue

        # If current also changed: incoming vs current diverge -> conflict.
        conflicts.append(
            Conflict(
                path="project.dependencies",
                current_repr=cur_val,
                incoming_repr=inc_val or "",
                reason=f"'{k}' modified in both incoming and current; current ranges kept.",
            )
        )

    # Rewrite the list in current order + new entries (stable)
    # Preserve current's ordering as much as possible.
    ordered: list[str] = []
    seen = set()

    for s in cur_list:
        k, _ = _norm_req_name(s)
        if k in cur and k not in seen:
            ordered.append(cur[k])
            seen.add(k)

    for k in sorted(cur.keys()):
        if k not in seen:
            ordered.append(cur[k])
            seen.add(k)

    _set_deps(current_doc, ordered)


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
    """Yield all leaf paths (tables included as leaf if non-dict)."""
    prefix = prefix or []
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_paths(v, prefix + [str(k)])
    else:
        yield prefix


def _is_version_path(path: list[str]) -> bool:
    return path == ["project", "version"]


def merge(base: str, current: str, incoming: str) -> str:
    """
    Merge driver entrypoint.
    - base/current/incoming: TOML contents (str)
    - Returns the merged text (with conflicts appended at end of file if needed)
    """
    base_doc = tomlkit.parse(base) if base.strip() else tomlkit.document()
    cur_doc = tomlkit.parse(current) if current.strip() else tomlkit.document()
    inc_doc = tomlkit.parse(incoming) if incoming.strip() else tomlkit.document()

    conflicts: list[Conflict] = []

    # 1) General merge (current wins, unless current hasn't changed and incoming has)
    # 3-way strategy per path (leaf), ignoring project.version.
    base_paths = set(tuple(p) for p in _iter_paths(base_doc))
    cur_paths = set(tuple(p) for p in _iter_paths(cur_doc))
    inc_paths = set(tuple(p) for p in _iter_paths(inc_doc))
    all_paths = base_paths | cur_paths | inc_paths

    for tpath in sorted(all_paths):
        path = list(tpath)
        if not path or _is_version_path(path):
            continue

        b = _toml_get(base_doc, path)
        c = _toml_get(cur_doc, path)
        i = _toml_get(inc_doc, path)

        # If incoming has nothing here: nothing to do
        if i is None and b is None:
            continue

        # Simple 3-way case
        if c == b and i != b:
            # current didn't touch it -> take incoming
            _toml_set(cur_doc, path, i)
        elif i == b:
            # incoming didn't touch it -> keep current
            continue
        else:
            # Both changed differently -> conflict (unless equal)
            if c != i:
                conflicts.append(
                    Conflict(
                        path=".".join(path),
                        current_repr=_dumps_value_as_toml(c),
                        incoming_repr=_dumps_value_as_toml(i),
                        reason="Concurrent changes (3-way).",
                    )
                )

    # 2) Special-case dependencies
    _merge_dependencies(base_doc, cur_doc, inc_doc, conflicts)

    merged = tomlkit.dumps(cur_doc).rstrip() + "\n"

    # 3) Append conflicts (if any) at end of file (visible on GitHub)
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
