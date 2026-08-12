"""Tests for database.factory module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from database.external_database import ExternalDatabase
from database.factory import add_database, build_database
from database.internal_database import InternalDatabase


def _internal_kwargs(tmp_path: Path) -> dict[str, object]:
    return {
        "database": "db",
        "user": "user",
        "password": "pwd",
        "schema_paths": [tmp_path / "schema.sql"],
        "psql_path": tmp_path / "pg" / "bin" / "psql",
        "pg_dir": tmp_path / "pg",
        "pg_data": tmp_path / "pg" / "data",
        "log_path": tmp_path / "pg" / "logs" / "postgres.log",
        "admin_password": "admin",
    }


def _external_kwargs(tmp_path: Path) -> dict[str, object]:
    return {
        "database": "db",
        "user": "user",
        "password": "pwd",
        "psql_path": tmp_path / "pg" / "bin" / "psql",
        "schema_paths": [tmp_path / "schema.sql"],
    }


class TestAddDatabase:
    """Test cases for add_database."""

    def test_adddatabase_internal_builds_internal_backend(self, tmp_path: Path) -> None:
        result = add_database("internal", **_internal_kwargs(tmp_path))

        assert isinstance(result, InternalDatabase)

    def test_adddatabase_external_builds_external_backend(self, tmp_path: Path) -> None:
        result = add_database("external", **_external_kwargs(tmp_path))

        assert isinstance(result, ExternalDatabase)

    def test_adddatabase_invalid_mode_raises(self) -> None:
        with pytest.raises(ModuleNotFoundError):
            add_database("unknown")  # type: ignore[arg-type]


class TestBuildDatabase:
    """Test cases for build_database."""

    def test_builddatabase_external_uses_db_host_and_returns_prepared_backend(
        self, tmp_path: Path
    ) -> None:
        mock_backend = MagicMock()
        pg_dir = tmp_path / "pg"
        with patch("database.factory.add_database", return_value=mock_backend) as mock_add:
            result = build_database(
                schema_paths=[tmp_path / "schema.sql"],
                db_host="db.example.com",
                db_port=5432,
                db_user="app_user",
                password="app-pwd",  # noqa: S106
                db_name="app_db",
                workarea_path=tmp_path / "workarea",
                pg_dir=pg_dir,
            )

        mock_add.assert_called_once()
        call_kwargs = mock_add.call_args.kwargs
        assert mock_add.call_args.args == ("external",) or call_kwargs.get("mode") == "external"
        assert call_kwargs["host"] == "db.example.com"
        assert call_kwargs["user"] == "app_user"
        assert call_kwargs["password"] == "app-pwd"  # noqa: S105
        assert call_kwargs["psql_path"] == pg_dir / "bin" / "psql"
        assert call_kwargs["allow_schema_creation"] is True
        mock_backend.prepare.assert_called_once()
        mock_backend.initialize.assert_called_once()
        assert result is mock_backend

    def test_builddatabase_internal_uses_pg_dir_and_workarea_paths(self, tmp_path: Path) -> None:
        mock_backend = MagicMock()
        workarea_path = tmp_path / "workarea"
        pg_dir = tmp_path / "pg"
        with patch("database.factory.add_database", return_value=mock_backend) as mock_add:
            build_database(
                schema_paths=[tmp_path / "schema.sql"],
                db_host=None,
                db_port=5432,
                db_user="app_user",
                password="app-pwd",  # noqa: S106
                db_name="app_db",
                workarea_path=workarea_path,
                pg_dir=pg_dir,
            )

        call_kwargs = mock_add.call_args.kwargs
        assert call_kwargs.get("mode") == "internal" or mock_add.call_args.args == ("internal",)
        assert call_kwargs["pg_dir"] == pg_dir
        assert call_kwargs["psql_path"] == pg_dir / "bin" / "psql"
        assert call_kwargs["pg_data"] == workarea_path / "var" / "db"
        assert call_kwargs["log_path"] == workarea_path / "logs" / "postgres.log"
        assert call_kwargs["admin_user"] == "postgres"

    def test_builddatabase_without_pg_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="pg_dir"):
            build_database(
                schema_paths=[tmp_path / "schema.sql"],
                db_host=None,
                db_port=5432,
                db_user="app_user",
                password="app-pwd",  # noqa: S106
                db_name="app_db",
                workarea_path=tmp_path / "workarea",
            )

    def test_builddatabase_external_without_pg_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="pg_dir"):
            build_database(
                schema_paths=[tmp_path / "schema.sql"],
                db_host="db.example.com",
                db_port=5432,
                db_user="app_user",
                password="app-pwd",  # noqa: S106
                db_name="app_db",
                workarea_path=tmp_path / "workarea",
            )
