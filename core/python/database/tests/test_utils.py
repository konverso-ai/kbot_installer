"""Tests for database.utils module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from database.base import DbSettings
from database.utils import (
    SCHEMA_VERSION_TABLE,
    apply_missing_upgrades,
    apply_schema,
    connect,
    ensure_version_table,
    execute_sql_file,
    get_applied_version,
    is_database_empty,
    mark_version_applied,
    upgrade_files,
    version_from_upgrade_file,
)
from utils.utils_for_unit_tests import compare


@pytest.fixture
def settings(tmp_path: Path) -> DbSettings:
    return DbSettings(
        database="db",
        user="user",
        password="password",
        schema_path=tmp_path / "schema.sql",
        pg_dir=tmp_path / "pg",
    )


@pytest.fixture
def mock_connect() -> MagicMock:
    with patch("database.utils.psycopg.connect") as mock:
        yield mock


@pytest.fixture
def mock_conn(mock_connect: MagicMock) -> MagicMock:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    mock_connect.return_value.__enter__.return_value = conn
    return conn


class TestConnect:
    """Test cases for connect."""

    def test_connect_valid_uses_settings_database(
        self, settings: DbSettings, mock_connect: MagicMock
    ) -> None:
        connect(settings)

        mock_connect.assert_called_once_with(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=settings.password,
        )

    def test_connect_valid_overrides_database(
        self, settings: DbSettings, mock_connect: MagicMock
    ) -> None:
        connect(settings, database="other_db")

        mock_connect.assert_called_once_with(
            host=settings.host,
            port=settings.port,
            dbname="other_db",
            user=settings.user,
            password=settings.password,
        )


class TestExecuteSqlFile:
    """Test cases for execute_sql_file."""

    def test_executesqlfile_valid_executes_file_content(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
        tmp_path: Path,
    ) -> None:
        sql_path = tmp_path / "script.sql"
        sql_path.write_text("SELECT 1;", encoding="utf-8")

        execute_sql_file(settings, sql_path)

        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.execute.assert_called_once_with(b"SELECT 1;")


class TestEnsureVersionTable:
    """Test cases for ensure_version_table."""

    def test_ensureversiontable_valid_creates_table(
        self, settings: DbSettings, mock_conn: MagicMock
    ) -> None:
        ensure_version_table(settings)

        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.execute.assert_called_once()
        assert compare("in", SCHEMA_VERSION_TABLE, cur.execute.call_args[0][0])


class TestGetAppliedVersion:
    """Test cases for get_applied_version."""

    def test_getappliedversion_valid_returns_versions(
        self, settings: DbSettings, mock_conn: MagicMock
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [("1.0.0",), ("1.0.1",)]

        result = get_applied_version(settings)

        assert compare("eq", result, {"1.0.0", "1.0.1"})

    def test_getappliedversion_valid_ensures_table_first(
        self, settings: DbSettings, mock_conn: MagicMock
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []

        get_applied_version(settings)

        assert compare("eq", cur.execute.call_count, 2)


class TestMarkVersionApplied:
    """Test cases for mark_version_applied."""

    def test_markversionapplied_valid_inserts_version(
        self, settings: DbSettings, mock_conn: MagicMock
    ) -> None:
        mark_version_applied(settings, "1.0.0")

        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0]
        assert compare("in", SCHEMA_VERSION_TABLE, args[0])
        assert compare("eq", args[1], ("1.0.0",))


class TestIsDatabaseEmpty:
    """Test cases for is_database_empty."""

    @pytest.mark.parametrize(
        "count, expected",
        [(0, True), (3, False)],
    )
    def test_isdatabaseempty_valid_reflects_table_count(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
        count: int,
        expected: bool,  # noqa: FBT001
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (count,)

        assert compare("eq", is_database_empty(settings), expected)


class TestApplySchema:
    """Test cases for apply_schema."""

    def test_applyschema_valid_executes_schema_and_marks_version(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
    ) -> None:
        settings.schema_path.parent.mkdir(parents=True, exist_ok=True)
        settings.schema_path.write_text("CREATE TABLE foo();", encoding="utf-8")
        settings.target_version = "1.0.0"

        apply_schema(settings)

        cur = mock_conn.cursor.return_value.__enter__.return_value
        executed_sql = [call.args[0] for call in cur.execute.call_args_list]
        assert compare("in", b"CREATE TABLE foo();", executed_sql)
        assert compare(
            "in",
            ("1.0.0",),
            [call.args[1] for call in cur.execute.call_args_list if len(call.args) > 1],
        )

    def test_applyschema_valid_skips_marking_version_without_target(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
    ) -> None:
        settings.schema_path.parent.mkdir(parents=True, exist_ok=True)
        settings.schema_path.write_text("CREATE TABLE foo();", encoding="utf-8")

        apply_schema(settings)

        cur = mock_conn.cursor.return_value.__enter__.return_value
        for call in cur.execute.call_args_list:
            assert compare("eq", len(call.args), 1)


class TestUpgradeFiles:
    """Test cases for upgrade_files."""

    def test_upgradefiles_valid_returns_empty_without_upgrades_dir(
        self, settings: DbSettings
    ) -> None:
        assert compare("eq", upgrade_files(settings), [])

    def test_upgradefiles_valid_returns_sorted_upgrade_files(
        self, settings: DbSettings, tmp_path: Path
    ) -> None:
        upgrades_dir = tmp_path / "upgrades"
        upgrades_dir.mkdir()
        (upgrades_dir / "upgrade_2.sql").write_text("", encoding="utf-8")
        (upgrades_dir / "upgrade_1.sql").write_text("", encoding="utf-8")
        (upgrades_dir / "not_an_upgrade.sql").write_text("", encoding="utf-8")
        settings.upgrades_dir = upgrades_dir

        result = upgrade_files(settings)

        assert compare(
            "eq",
            [path.name for path in result],
            ["upgrade_1.sql", "upgrade_2.sql"],
        )


class TestVersionFromUpgradeFile:
    """Test cases for version_from_upgrade_file."""

    def test_versionfromupgradefile_valid_strips_prefix(self) -> None:
        assert compare(
            "eq",
            version_from_upgrade_file(Path("/upgrades/upgrade_1.2.3.sql")),
            "1.2.3",
        )


class TestApplyMissingUpgrades:
    """Test cases for apply_missing_upgrades."""

    def test_applymissingupgrades_valid_applies_only_missing_versions(
        self, settings: DbSettings, tmp_path: Path
    ) -> None:
        upgrades_dir = tmp_path / "upgrades"
        upgrades_dir.mkdir()
        (upgrades_dir / "upgrade_1.sql").write_text("ALTER 1;", encoding="utf-8")
        (upgrades_dir / "upgrade_2.sql").write_text("ALTER 2;", encoding="utf-8")
        settings.upgrades_dir = upgrades_dir

        with (
            patch("database.utils.get_applied_version", return_value={"1"}),
            patch("database.utils.execute_sql_file") as mock_execute,
            patch("database.utils.mark_version_applied") as mock_mark,
        ):
            apply_missing_upgrades(settings)

            mock_execute.assert_called_once_with(
                settings=settings, path=upgrades_dir / "upgrade_2.sql"
            )
            mock_mark.assert_called_once_with(settings=settings, version="2")

    def test_applymissingupgrades_valid_applies_nothing_when_up_to_date(
        self, settings: DbSettings, tmp_path: Path
    ) -> None:
        upgrades_dir = tmp_path / "upgrades"
        upgrades_dir.mkdir()
        (upgrades_dir / "upgrade_1.sql").write_text("ALTER 1;", encoding="utf-8")
        settings.upgrades_dir = upgrades_dir

        with (
            patch("database.utils.get_applied_version", return_value={"1"}),
            patch("database.utils.execute_sql_file") as mock_execute,
            patch("database.utils.mark_version_applied") as mock_mark,
        ):
            apply_missing_upgrades(settings)

            mock_execute.assert_not_called()
            mock_mark.assert_not_called()
