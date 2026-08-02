"""Tests for installer_support.thirdparty_env."""

import os
from pathlib import Path

import pytest

from installer_support.thirdparty_env import (
    parse_env_file,
    prepend_thirdparty_ld_library_path,
    resolve_pg_dir,
    resolve_pg_dir_str,
    thirdparty_ld_library_path,
)

_VERSIONS_ENV = """\
# A comment line
PYTHON_VERSION=3.10.15
PG_VERSION=11.5
SSL_VERSION=3.6.2

THIRDPARTY_PATH=${THIRDPARTY_HOME}

PYTHON_DIR=${THIRDPARTY_PATH}/Python-${PYTHON_VERSION}
PG_DIR=${THIRDPARTY_PATH}/postgresql-${PG_VERSION}
SSL_DIR=${THIRDPARTY_PATH}/openssl-${SSL_VERSION}
"""


def _write_versions_env(installer_path: Path, content: str = _VERSIONS_ENV) -> Path:
    thirdparty = installer_path / "3rdparty"
    thirdparty.mkdir(parents=True, exist_ok=True)
    versions_env = thirdparty / "versions.env"
    versions_env.write_text(content, encoding="utf-8")
    return thirdparty


class TestParseEnvFile:
    """Tests for parse_env_file."""

    def test_substitutes_base_and_previous_vars(self, tmp_path) -> None:
        """${VAR} references resolve against base_vars and previously parsed values."""
        env_file = tmp_path / "versions.env"
        env_file.write_text(_VERSIONS_ENV, encoding="utf-8")

        result = parse_env_file(env_file, {"THIRDPARTY_HOME": "/opt/tp"})

        assert result["PYTHON_DIR"] == "/opt/tp/Python-3.10.15"
        assert result["PG_DIR"] == "/opt/tp/postgresql-11.5"
        assert result["SSL_DIR"] == "/opt/tp/openssl-3.6.2"
        assert "THIRDPARTY_HOME" not in result

    def test_ignores_comments_and_blank_lines(self, tmp_path) -> None:
        """Comment and blank lines produce no entries."""
        env_file = tmp_path / "versions.env"
        env_file.write_text("# only a comment\n\n   \n", encoding="utf-8")

        assert parse_env_file(env_file) == {}

    def test_unknown_reference_becomes_empty(self, tmp_path) -> None:
        """A reference to an unknown variable expands to an empty string."""
        env_file = tmp_path / "versions.env"
        env_file.write_text("FOO=${MISSING}/bar\n", encoding="utf-8")

        assert parse_env_file(env_file) == {"FOO": "/bar"}


class TestResolvePgDir:
    """Tests for resolve_pg_dir."""

    def test_resolves_from_versions_env(self, tmp_path) -> None:
        """PG_DIR is resolved relative to the installer's 3rdparty directory."""
        thirdparty = _write_versions_env(tmp_path)

        assert resolve_pg_dir(tmp_path) == thirdparty / "postgresql-11.5"

    def test_returns_none_when_file_missing(self, tmp_path) -> None:
        """A missing versions.env yields None."""
        assert resolve_pg_dir(tmp_path) is None

    def test_returns_none_when_pg_dir_absent(self, tmp_path) -> None:
        """A versions.env without PG_DIR yields None."""
        _write_versions_env(tmp_path, "PYTHON_VERSION=3.10.15\n")

        assert resolve_pg_dir(tmp_path) is None


class TestThirdpartyLdLibraryPath:
    """Tests for thirdparty_ld_library_path."""

    def test_keeps_only_existing_dirs_in_env_order(self, tmp_path) -> None:
        """Only existing library dirs are returned, in env.sh order."""
        thirdparty = _write_versions_env(tmp_path)
        # Create PG_DIR/lib and SSL_DIR/lib64 only; leave PYTHON_DIR/lib absent.
        (thirdparty / "postgresql-11.5" / "lib").mkdir(parents=True)
        (thirdparty / "openssl-3.6.2" / "lib64").mkdir(parents=True)

        result = thirdparty_ld_library_path(tmp_path)

        assert result == ":".join(
            [
                str(thirdparty / "postgresql-11.5" / "lib"),
                str(thirdparty / "openssl-3.6.2" / "lib64"),
            ]
        )

    def test_returns_none_when_file_missing(self, tmp_path) -> None:
        """A missing versions.env yields None."""
        assert thirdparty_ld_library_path(tmp_path) is None

    def test_returns_none_when_no_dir_exists(self, tmp_path) -> None:
        """When no resolved library directory exists on disk, returns None."""
        _write_versions_env(tmp_path)

        assert thirdparty_ld_library_path(tmp_path) is None


class TestResolvePgDirStr:
    """Tests for resolve_pg_dir_str."""

    def test_resolves_from_versions_env(self, tmp_path) -> None:
        """PG_DIR is resolved as a string relative to the 3rdparty directory."""
        thirdparty = _write_versions_env(tmp_path)

        assert resolve_pg_dir_str(tmp_path) == str(thirdparty / "postgresql-11.5")

    def test_returns_none_when_file_missing(self, tmp_path) -> None:
        """A missing versions.env yields None."""
        assert resolve_pg_dir_str(tmp_path) is None


class TestPrependThirdpartyLdLibraryPath:
    """Tests for prepend_thirdparty_ld_library_path."""

    @pytest.fixture(autouse=True)
    def _clean_ld_library_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    def test_prepends_resolved_dirs_to_empty_env(self, tmp_path) -> None:
        """Resolved 3rdparty library dirs are prepended when LD_LIBRARY_PATH is unset."""
        thirdparty = _write_versions_env(tmp_path)
        (thirdparty / "postgresql-11.5" / "lib").mkdir(parents=True)

        prepend_thirdparty_ld_library_path(tmp_path)

        assert os.environ["LD_LIBRARY_PATH"] == str(thirdparty / "postgresql-11.5" / "lib")

    def test_prepends_without_duplicating_existing_entries(self, tmp_path) -> None:
        """Existing LD_LIBRARY_PATH entries are kept, without duplicating already-present ones."""
        thirdparty = _write_versions_env(tmp_path)
        pg_lib = thirdparty / "postgresql-11.5" / "lib"
        pg_lib.mkdir(parents=True)
        os.environ["LD_LIBRARY_PATH"] = f"/already/there{os.pathsep}{pg_lib}"

        prepend_thirdparty_ld_library_path(tmp_path)

        assert os.environ["LD_LIBRARY_PATH"] == f"/already/there{os.pathsep}{pg_lib}"

    def test_is_idempotent(self, tmp_path) -> None:
        """Calling the function twice does not duplicate entries."""
        thirdparty = _write_versions_env(tmp_path)
        (thirdparty / "postgresql-11.5" / "lib").mkdir(parents=True)

        prepend_thirdparty_ld_library_path(tmp_path)
        first = os.environ["LD_LIBRARY_PATH"]
        prepend_thirdparty_ld_library_path(tmp_path)

        assert os.environ["LD_LIBRARY_PATH"] == first

    def test_noop_when_no_thirdparty_path_resolved(self, tmp_path) -> None:
        """When no library directory can be resolved, LD_LIBRARY_PATH is left untouched."""
        prepend_thirdparty_ld_library_path(tmp_path)

        assert "LD_LIBRARY_PATH" not in os.environ
