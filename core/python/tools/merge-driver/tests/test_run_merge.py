"""Tests for run_merge.py (git merge driver CLI)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import run_merge  # noqa: PLC0415 - need to run main() for coverage


def test_main_wrong_arg_count():
    """Wrong number of arguments -> exit 2."""
    with patch.object(run_merge.sys, "argv", ["run_merge.py", "a", "b"]):
        assert run_merge.main() == 2


def test_main_missing_file(tmp_path: Path):
    """Missing one of the three files -> exit 1."""
    base = tmp_path / "base.toml"
    current = tmp_path / "current.toml"
    incoming = tmp_path / "incoming.toml"
    base.write_text("[project]\nname = 'x'\n")
    current.write_text("[project]\nname = 'x'\n")
    # incoming does not exist
    with patch.object(
        run_merge.sys,
        "argv",
        ["run_merge.py", str(base), str(current), str(incoming)],
    ):
        assert run_merge.main() == 1


def test_main_success_no_conflict(tmp_path: Path):
    """Clean merge -> exit 0, result written to current."""
    base = tmp_path / "base.toml"
    current = tmp_path / "current.toml"
    incoming = tmp_path / "incoming.toml"
    base.write_text("[project]\nname = 'demo'\nversion = '0.1.0'\n")
    current.write_text("[project]\nname = 'demo'\nversion = '0.2.0'\n")
    incoming.write_text("[project]\nname = 'demo'\nversion = '0.1.0'\n[tool.other]\nkey = 1\n")
    with patch.object(
        run_merge.sys,
        "argv",
        ["run_merge.py", str(base), str(current), str(incoming)],
    ):
        assert run_merge.main() == 0
    # Incoming added [tool.other], version stays current
    out = current.read_text()
    assert "0.2.0" in out and "version" in out
    assert "[tool.other]" in out
    assert "key = 1" in out
    assert "<<<<<<<" not in out


def test_main_conflict_returns_nonzero(tmp_path: Path):
    """Merge with conflicts -> exit 1 so git does not auto-stage invalid TOML."""
    base = tmp_path / "base.toml"
    current = tmp_path / "current.toml"
    incoming = tmp_path / "incoming.toml"
    base.write_text(
        "[project]\nname = 'demo'\nversion = '0.1.0'\n\n[tool.demo]\nmode = 'A'\n"
    )
    current.write_text(
        "[project]\nname = 'demo'\nversion = '0.2.0'\n\n[tool.demo]\nmode = 'C'\n"
    )
    incoming.write_text(
        "[project]\nname = 'demo'\nversion = '0.1.0'\n\n[tool.demo]\nmode = 'B'\n"
    )
    with patch.object(
        run_merge.sys,
        "argv",
        ["run_merge.py", str(base), str(current), str(incoming)],
    ):
        assert run_merge.main() == 1
    # File still written with conflict markers (user resolves manually)
    out = current.read_text()
    assert "<<<<<<< CURRENT" in out
    assert "=======" in out
    assert ">>>>>>> INCOMING" in out
