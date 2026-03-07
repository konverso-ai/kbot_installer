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
        # dependencies:
        # incoming adds a dep while current modified an existing one
        # -> new dep added + 3-way conflict on the whole deps list
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

                # ===== MERGE CONFLICTS (manual resolution required) =====
                # [1] Path: project.dependencies
                # Reason: Concurrent changes (3-way).
                <<<<<<< CURRENT
                ["ansible==3.0.0"]
                =======
                ["ansible==2.0.0", "snow>=2026.1"]
                >>>>>>> INCOMING
            """),
        ),

        # ---------------------------------------------------------
        # CASE 7
        # dependencies:
        # incoming removes a dep, current modified it
        # -> dep kept in current + removal conflict
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

                # ===== MERGE CONFLICTS (manual resolution required) =====
                # [1] Path: project.dependencies
                # Reason: Concurrent changes (3-way).
                <<<<<<< CURRENT
                ["ansible==2.0.0", "snow>=2026.2"]
                =======
                ["ansible==2.0.0"]
                >>>>>>> INCOMING
                # [2] Path: project.dependencies
                # Reason: Incoming removes 'snow' but current has modified it since base.
                <<<<<<< CURRENT
                snow>=2026.2
                =======
                (removed)
                >>>>>>> INCOMING
            """),
        ),

        # ---------------------------------------------------------
        # CASE 8
        # dependencies:
        # incoming modifies a dep, current removed it -> conflict
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
                dependencies = ["ansible==2.0.0"]

                # ===== MERGE CONFLICTS (manual resolution required) =====
                # [1] Path: project.dependencies
                # Reason: Concurrent changes (3-way).
                <<<<<<< CURRENT
                ["ansible==2.0.0"]
                =======
                ["ansible==2.0.0", "snow>=2026.2"]
                >>>>>>> INCOMING
                # [2] Path: project.dependencies
                # Reason: Incoming modifies 'snow' but current has removed it.
                <<<<<<< CURRENT
                (removed)
                =======
                snow>=2026.2
                >>>>>>> INCOMING
            """),
        ),

        # ---------------------------------------------------------
        # CASE 9
        # dependencies:
        # both modify same dep differently + incoming changes
        # another dep that current left unchanged
        # -> current kept for both + conflict for diverging dep
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
                dependencies = ["ansible==3.0.0", "snow>=2026.1"]

                # ===== MERGE CONFLICTS (manual resolution required) =====
                # [1] Path: project.dependencies
                # Reason: Concurrent changes (3-way).
                <<<<<<< CURRENT
                ["ansible==3.0.0", "snow>=2026.1"]
                =======
                ["ansible==4.0.0", "snow>=2026.2"]
                >>>>>>> INCOMING
                # [2] Path: project.dependencies
                # Reason: 'ansible' modified in both incoming and current; current ranges kept.
                <<<<<<< CURRENT
                ansible==3.0.0
                =======
                ansible==4.0.0
                >>>>>>> INCOMING
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
    conflicts = []
    _merge_dependencies(base_doc, cur_doc, inc_doc, conflicts)
    assert conflicts == []
    assert cur_doc["project"]["dependencies"] == ["pkg==1.0.0"]


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
