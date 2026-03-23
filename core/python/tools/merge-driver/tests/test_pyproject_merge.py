from __future__ import annotations

from textwrap import dedent
from unittest.mock import patch

import pytest

from pyproject_merge import merge
from pyproject_merge import _merge_dependencies


def D(s: str) -> str:
    """Cleanup of TOML blocks to avoid surprises."""
    return dedent(s).strip() + "\n"


@pytest.mark.parametrize(
    "params",
    [
        # ---------------------------------------------------------
        # CASE 1
        # version: current always wins
        # incoming tries to impose another version -> ignored
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
            """),
            current=D("""
                [project]
                name = "demo"
                version = "1.0.0"
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "9.9.9"
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "1.0.0"
            """),
        ),

        # ---------------------------------------------------------
        # CASE 2
        # standard field:
        # current unchanged vs base -> incoming is applied
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"

                [tool.demo]
                mode = "A"
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"

                [tool.demo]
                mode = "A"
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"

                [tool.demo]
                mode = "B"
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"

                [tool.demo]
                mode = "B"
            """),
        ),

        # ---------------------------------------------------------
        # CASE 3
        # dependencies:
        # incoming adds a dependency absent from current
        # -> it is added
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1,<2026.2"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1,<2026.2"]
            """),
        ),

        # ---------------------------------------------------------
        # CASE 4
        # dependencies:
        # incoming removes a dependency
        # current hasn't modified it -> it is removed
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1,<2026.2"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1,<2026.2"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0"]
            """),
        ),

        # ---------------------------------------------------------
        # CASE 5
        # 3-way conflict:
        # current and incoming modify differently
        # -> current kept + conflict block appended
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"

                [tool.demo]
                mode = "A"
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"

                [tool.demo]
                mode = "C"
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"

                [tool.demo]
                mode = "B"
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"

                [tool.demo]
                mode = "C"

                # ===== MERGE CONFLICTS (manual resolution required) =====
                # [1] Path: tool.demo.mode
                # Reason: Concurrent changes (3-way).
                <<<<<<< CURRENT
                "C"
                =======
                "B"
                >>>>>>> INCOMING
            """),
        ),

        # ---------------------------------------------------------
        # CASE 6
        # dependencies: per-package newer specifier wins; added deps merged in
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==3.0.0"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==3.0.0", "snow>=2026.1"]
            """),
        ),

        # ---------------------------------------------------------
        # CASE 7
        # dependencies: incoming removes dep; current had bumped it vs base -> keep current's newer pin
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.2"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.2"]
            """),
        ),

        # ---------------------------------------------------------
        # CASE 8
        # dependencies: current dropped a dep; incoming still has it -> take incoming (re-add newer pin)
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.2"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.2"]
            """),
        ),

        # ---------------------------------------------------------
        # CASE 9
        # dependencies: both sides change pins -> pick newer for each package name
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==3.0.0", "snow>=2026.1"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==4.0.0", "snow>=2026.2"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==4.0.0", "snow>=2026.2"]
            """),
        ),

        # ---------------------------------------------------------
        # CASE 10
        # incoming adds a new TOML section not in base/current
        # -> section is added to current
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"

                [tool.newsection]
                key = "val"
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"

                [tool.newsection]
                key = "val"
            """),
        ),

        # ---------------------------------------------------------
        # CASE 11
        # current adds a field not in base or incoming
        # -> current's field is preserved
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                description = "hello"
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                description = "hello"
            """),
        ),

        # ---------------------------------------------------------
        # CASE 12
        # base has no [project] (e.g. empty or tool-only)
        # -> _get_deps(base_doc) returns [] (proj is None)
        # ---------------------------------------------------------
        dict(
            base="",
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
            """),
        ),

        # ---------------------------------------------------------
        # CASE 13
        # both current and incoming removed the same dependency
        # -> no conflict, dep stays removed (continue when cur_val is None)
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0"]
            """),
        ),

        # CASE 14
        # incoming removes a dep, current unchanged from base for that dep
        # -> dep removed (del cur[k] when base_val == cur_val)
        # Use a single exact-version dep so canonical form matches
        # ---------------------------------------------------------
        dict(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "pkg==1.0.0"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0", "pkg==1.0.0"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0"]
            """),
            expected=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0"]
            """),
        ),
    ],
)
def test_merge(params: dict):
    expected = params.pop("expected")
    actual = merge(**params)
    assert actual == expected


def test_merge_dependencies_removal_unchanged():
    """Cover _merge_dependencies path: incoming removes dep, current unchanged (del cur[k])."""
    import tomlkit
    base_doc = tomlkit.parse(D("""
        [project]
        name = "demo"
        version = "0.1.0"
        dependencies = ["pkg==1.0.0", "other==2.0.0"]
    """))
    cur_doc = tomlkit.parse(D("""
        [project]
        name = "demo"
        version = "0.2.0"
        dependencies = ["pkg==1.0.0", "other==2.0.0"]
    """))
    inc_doc = tomlkit.parse(D("""
        [project]
        name = "demo"
        version = "0.1.0"
        dependencies = ["pkg==1.0.0"]
    """))
    _merge_dependencies(base_doc, cur_doc, inc_doc)
    assert list(cur_doc["project"]["dependencies"]) == ["pkg==1.0.0"]


def test_merge_dependencies_current_removal_unchanged():
    """Current removes a dep; incoming unchanged vs base — accept removal (symmetric 3-way merge)."""
    import tomlkit

    base_doc = tomlkit.parse(D("""
        [project]
        name = "demo"
        version = "0.1.0"
        dependencies = ["pkg==1.0.0", "other==2.0.0"]
    """))
    cur_doc = tomlkit.parse(D("""
        [project]
        name = "demo"
        version = "0.2.0"
        dependencies = ["other==2.0.0"]
    """))
    inc_doc = tomlkit.parse(D("""
        [project]
        name = "demo"
        version = "0.1.0"
        dependencies = ["pkg==1.0.0", "other==2.0.0"]
    """))
    _merge_dependencies(base_doc, cur_doc, inc_doc)
    assert list(cur_doc["project"]["dependencies"]) == ["other==2.0.0"]


def test_merge_without_packaging():
    """Fallback path when packaging is not available."""
    with patch("pyproject_merge.Requirement", None):
        actual = merge(
            base=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0"]
            """),
            current=D("""
                [project]
                name = "demo"
                version = "0.2.0"
                dependencies = ["ansible==2.0.0"]
            """),
            incoming=D("""
                [project]
                name = "demo"
                version = "0.1.0"
                dependencies = ["ansible==2.0.0", "snow>=2026.1,<2026.2"]
            """),
        )
    expected = D("""
        [project]
        name = "demo"
        version = "0.2.0"
        dependencies = ["ansible==2.0.0", "snow>=2026.1,<2026.2"]
    """)
    assert actual == expected


def test_merge_dependencies_preserves_multiline_when_any_side_multiline() -> None:
    """Merged project.dependencies stays multiline when base/current/incoming use multiline style."""
    actual = merge(
        base=D("""
            [project]
            name = "demo"
            version = "0.1.0"
            dependencies = [
                "ansible==2.0.0",
            ]
        """),
        current=D("""
            [project]
            name = "demo"
            version = "0.2.0"
            dependencies = [
                "ansible==2.0.0",
            ]
        """),
        incoming=D("""
            [project]
            name = "demo"
            version = "0.1.0"
            dependencies = [
                "ansible==2.0.0",
                "snow>=2026.1,<2026.2",
            ]
        """),
    )
    i = actual.find("dependencies = [")
    j = actual.find("]", i)
    assert i != -1 and j != -1
    assert actual[i:j].count("\n") >= 2
    assert "snow>=2026.1,<2026.2" in actual


def test_merge_tool_uv_sources_union_restores_from_incoming() -> None:
    """tool.uv.sources is union-merged: current dropped the section but incoming still has entries -> restored."""
    actual = merge(
        base=D("""
            [project]
            name = "kbot"
            version = "2026.2.dev0"

            [tool.uv.sources]
            snow = { workspace = true }
        """),
        current=D("""
            [project]
            name = "kbot"
            version = "2026.2.dev2"
        """),
        incoming=D("""
            [project]
            name = "kbot"
            version = "2026.1.dev1"

            [tool.uv.sources]
            snow = { workspace = true }
        """),
    )
    assert "[tool.uv.sources]" in actual
    assert "snow = { workspace = true }" in actual
    assert "2026.2.dev2" in actual


def test_merge_tool_uv_index_union_keeps_both_named_indexes() -> None:
    """[[tool.uv.index]] merged by name: current dropped one block, incoming still has both -> both kept."""
    actual = merge(
        base=D("""
            [project]
            name = "kbot"
            version = "0.1.0"

            [[tool.uv.index]]
            name = "konverso-nexus"
            url = "https://nexus.example/wheels/simple/"

            [[tool.uv.index]]
            name = "konverso-pypi-proxy"
            url = "https://nexus.example/pypi/simple"
            default = true
        """),
        current=D("""
            [project]
            name = "kbot"
            version = "0.2.0"

            [[tool.uv.index]]
            name = "konverso-nexus"
            url = "https://nexus.example/wheels/simple/"
        """),
        incoming=D("""
            [project]
            name = "kbot"
            version = "0.1.0"

            [[tool.uv.index]]
            name = "konverso-nexus"
            url = "https://nexus.example/wheels/simple/"

            [[tool.uv.index]]
            name = "konverso-pypi-proxy"
            url = "https://nexus.example/pypi/simple"
            default = true
        """),
    )
    assert actual.count("[[tool.uv.index]]") == 2
    assert "konverso-pypi-proxy" in actual
    assert "0.2.0" in actual


def test_incoming_removes_field_current_unchanged_vs_base() -> None:
    """Incoming deletes a key; current matches base — accept deletion (no None in TOML)."""
    actual = merge(
        base=D("""
            [project]
            name = "demo"
            version = "0.1.0"

            [tool.demo]
            extra = true
        """),
        current=D("""
            [project]
            name = "demo"
            version = "0.2.0"

            [tool.demo]
            extra = true
        """),
        incoming=D("""
            [project]
            name = "demo"
            version = "0.1.0"

            [tool.demo]
        """),
    )
    expected = D("""
        [project]
        name = "demo"
        version = "0.2.0"

        [tool.demo]
    """)
    assert actual == expected


def test_dumps_value_as_toml_none() -> None:
    from pyproject_merge import _dumps_value_as_toml

    assert _dumps_value_as_toml(None) == "<absent>"

