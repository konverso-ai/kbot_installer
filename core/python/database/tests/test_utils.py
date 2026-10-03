"""Tests for database.utils module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import click

from database.base import DbSettings
from database.utils import (
    DEFAULT_DB_PASSWORD,
    DatabaseDumpError,
    SCHEMA_VERSION_TABLE,
    SqlFileError,
    apply_missing_upgrades,
    apply_schema,
    connect,
    drop_owned_objects,
    dump_database,
    ensure_version_table,
    execute_sql_file,
    get_applied_version,
    is_database_empty,
    mark_version_applied,
    resolve_admin_password,
    resolve_db_password,
    safe_encrypt,
    set_admin_password,
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
        psql_path=tmp_path / "bin" / "psql",
        schema_paths=[tmp_path / "schema.sql"],
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


@pytest.fixture
def mock_subprocess_run() -> MagicMock:
    with patch("database.utils.subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=0, stderr="")
        yield mock


class TestConnect:
    """Test cases for connect."""

    def test_connect_valid_uses_settings_database(self, settings: DbSettings, mock_connect: MagicMock) -> None:
        connect(settings)

        mock_connect.assert_called_once_with(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=settings.password,
        )

    def test_connect_valid_overrides_database(self, settings: DbSettings, mock_connect: MagicMock) -> None:
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

    def test_executesqlfile_valid_invokes_psql_with_expected_arguments(
        self,
        settings: DbSettings,
        mock_subprocess_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        sql_path = tmp_path / "script.sql"
        sql_path.write_text("SELECT 1;", encoding="utf-8")

        execute_sql_file(settings, sql_path)

        mock_subprocess_run.assert_called_once()
        command = mock_subprocess_run.call_args.args[0]
        assert compare(
            "eq",
            command,
            [
                str(settings.psql_path),
                "-v",
                "ON_ERROR_STOP=1",
                "-q",
                "-h",
                settings.host,
                "-p",
                str(settings.port),
                "-U",
                settings.user,
                "-d",
                settings.database,
                "-f",
                str(sql_path),
            ],
        )
        env = mock_subprocess_run.call_args.kwargs["env"]
        assert compare("eq", env["PGPASSWORD"], settings.password)

    def test_executesqlfile_invalid_raises_when_psql_fails(
        self,
        settings: DbSettings,
        mock_subprocess_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        sql_path = tmp_path / "script.sql"
        sql_path.write_text("SELECT 1;", encoding="utf-8")
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="boom")

        with pytest.raises(SqlFileError, match="boom"):
            execute_sql_file(settings, sql_path)


class TestEnsureVersionTable:
    """Test cases for ensure_version_table."""

    def test_ensureversiontable_valid_creates_table(self, settings: DbSettings, mock_conn: MagicMock) -> None:
        ensure_version_table(settings)

        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.execute.assert_called_once()
        assert compare("in", SCHEMA_VERSION_TABLE, cur.execute.call_args[0][0])


class TestGetAppliedVersion:
    """Test cases for get_applied_version."""

    def test_getappliedversion_valid_returns_versions(self, settings: DbSettings, mock_conn: MagicMock) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [("1.0.0",), ("1.0.1",)]

        result = get_applied_version(settings)

        assert compare("eq", result, {"1.0.0", "1.0.1"})

    def test_getappliedversion_valid_ensures_table_first(self, settings: DbSettings, mock_conn: MagicMock) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []

        get_applied_version(settings)

        assert compare("eq", cur.execute.call_count, 2)


class TestMarkVersionApplied:
    """Test cases for mark_version_applied."""

    def test_markversionapplied_valid_inserts_version(self, settings: DbSettings, mock_conn: MagicMock) -> None:
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
        mock_subprocess_run: MagicMock,
    ) -> None:
        schema_path = settings.schema_paths[0]
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text("CREATE TABLE foo();", encoding="utf-8")
        settings.target_version = "1.0.0"

        apply_schema(settings)

        mock_subprocess_run.assert_called_once()
        assert compare("in", str(schema_path), mock_subprocess_run.call_args.args[0])

        cur = mock_conn.cursor.return_value.__enter__.return_value
        assert compare(
            "in",
            ("1.0.0",),
            [call.args[1] for call in cur.execute.call_args_list if len(call.args) > 1],
        )

    def test_applyschema_valid_skips_marking_version_without_target(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
        mock_subprocess_run: MagicMock,
    ) -> None:
        schema_path = settings.schema_paths[0]
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text("CREATE TABLE foo();", encoding="utf-8")

        apply_schema(settings)

        cur = mock_conn.cursor.return_value.__enter__.return_value
        for call in cur.execute.call_args_list:
            assert compare("eq", len(call.args), 1)

    def test_applyschema_valid_noop_when_schema_file_missing(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
        mock_subprocess_run: MagicMock,
    ) -> None:
        assert compare("eq", settings.schema_paths[0].exists(), False)

        apply_schema(settings)

        mock_subprocess_run.assert_not_called()
        mock_conn.cursor.assert_not_called()

    def test_applyschema_valid_applies_multiple_files_in_order(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
        mock_subprocess_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        dependency_schema = tmp_path / "dependency.sql"
        dependency_schema.write_text("CREATE TABLE dependency();", encoding="utf-8")
        top_schema = tmp_path / "top.sql"
        top_schema.write_text("CREATE TABLE top();", encoding="utf-8")
        settings.schema_paths = [dependency_schema, top_schema]

        apply_schema(settings)

        applied_files = [call.args[0][-1] for call in mock_subprocess_run.call_args_list]
        assert compare(
            "eq",
            applied_files,
            [str(dependency_schema), str(top_schema)],
        )

    def test_applyschema_valid_skips_missing_files_among_several(
        self,
        settings: DbSettings,
        mock_conn: MagicMock,
        mock_subprocess_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        missing_schema = tmp_path / "missing.sql"
        existing_schema = tmp_path / "existing.sql"
        existing_schema.write_text("CREATE TABLE existing();", encoding="utf-8")
        settings.schema_paths = [missing_schema, existing_schema]

        apply_schema(settings)

        applied_files = [call.args[0][-1] for call in mock_subprocess_run.call_args_list]
        assert compare("eq", applied_files, [str(existing_schema)])


class TestUpgradeFiles:
    """Test cases for upgrade_files."""

    def test_upgradefiles_valid_returns_empty_without_upgrades_dir(self, settings: DbSettings) -> None:
        assert compare("eq", upgrade_files(settings), [])

    def test_upgradefiles_valid_returns_sorted_upgrade_files(self, settings: DbSettings, tmp_path: Path) -> None:
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

            mock_execute.assert_called_once_with(settings=settings, path=upgrades_dir / "upgrade_2.sql")
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


class TestResolveDbPassword:
    """Tests for resolve_db_password."""

    def test_resolvedbpassword_valid_returns_explicit_password_unchanged(self) -> None:
        password, generated = resolve_db_password("explicit-pwd", no_password=False)

        assert password == "explicit-pwd"
        assert generated is None

    def test_resolvedbpassword_valid_prefers_explicit_password_over_no_password(self) -> None:
        password, generated = resolve_db_password("explicit-pwd", no_password=True)

        assert password == "explicit-pwd"
        assert generated is None

    def test_resolvedbpassword_valid_generates_random_password_when_no_password(self) -> None:
        password, generated = resolve_db_password(None, no_password=True)

        assert password == generated
        assert generated is not None
        assert len(generated) > 0

    def test_resolvedbpassword_valid_falls_back_to_default_password(self) -> None:
        password, generated = resolve_db_password(None, no_password=False)

        assert password == DEFAULT_DB_PASSWORD
        assert generated is None


class TestResolveAdminPassword:
    """Tests for resolve_admin_password."""

    def test_resolveadminpassword_valid_returns_env_password(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KBOT_ADMIN_PASSWORD", "env-pwd")

        password, generated = resolve_admin_password(no_password=False)

        assert password == "env-pwd"
        assert generated is None

    def test_resolveadminpassword_valid_prefers_env_password_over_no_password(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KBOT_ADMIN_PASSWORD", "env-pwd")

        password, generated = resolve_admin_password(no_password=True)

        assert password == "env-pwd"
        assert generated is None

    def test_resolveadminpassword_valid_generates_random_password_when_no_password(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KBOT_ADMIN_PASSWORD", raising=False)

        password, generated = resolve_admin_password(no_password=True)

        assert password == generated
        assert generated is not None
        assert len(generated) > 0

    def test_resolveadminpassword_invalid_raises_without_env_or_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KBOT_ADMIN_PASSWORD", raising=False)

        with pytest.raises(click.UsageError, match="KBOT_ADMIN_PASSWORD"):
            resolve_admin_password(no_password=False)


class TestDropOwnedObjects:
    """Tests for drop_owned_objects."""

    def test_dropownedobjects_valid_drops_owned_by_current_user(
        self, settings: DbSettings, mock_conn: MagicMock
    ) -> None:
        drop_owned_objects(settings)

        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.execute.assert_called_once_with("DROP OWNED BY CURRENT_USER")
        mock_conn.commit.assert_called_once()


class TestDumpDatabase:
    """Tests for dump_database."""

    def test_dumpdatabase_valid_invokes_pgdump_next_to_psql(
        self, settings: DbSettings, mock_subprocess_run: MagicMock, tmp_path: Path
    ) -> None:
        dump_path = tmp_path / "backups" / "dump.sql"

        dump_database(settings, dump_path)

        command = mock_subprocess_run.call_args.args[0]
        assert compare("eq", command[0], str(settings.psql_path.with_name("pg_dump")))
        assert compare("in", "--no-owner", command)
        assert compare("eq", command[command.index("-f") + 1], str(dump_path))
        assert compare("eq", command[-1], settings.database)
        assert compare("eq", mock_subprocess_run.call_args.kwargs["env"]["PGPASSWORD"], settings.password)
        assert compare("eq", dump_path.parent.is_dir(), True)

    def test_dumpdatabase_invalid_raises_when_pgdump_fails(
        self, settings: DbSettings, mock_subprocess_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="boom")

        with pytest.raises(DatabaseDumpError, match="boom"):
            dump_database(settings, tmp_path / "dump.sql")


class TestSafeEncrypt:
    """Tests for safe_encrypt."""

    # Produced by kbot's own 'utils.SafeEncrypt("K0nversOK!")' with the salt bytes(range(16)).
    KBOT_REFERENCE = (
        "YmU0NGU5ZDBmODFhODhkZjZmOGZhNzBlYmQzZjk1OGRlNTk2MzVlYTkwYTMwNzU5OTk3MjFlMmM4NGI5NjdhZSQAAQIDBAUGBwgJCgsMDQ4P"
    )

    def test_safeencrypt_valid_matches_kbot_reference_hash(self) -> None:
        with patch("database.utils.secrets.token_bytes", return_value=bytes(range(16))):
            assert compare("eq", safe_encrypt("K0nversOK!"), self.KBOT_REFERENCE)

    def test_safeencrypt_valid_verifies_like_kbot_with_stored_salt(self) -> None:
        assert compare("eq", safe_encrypt("K0nversOK!", self.KBOT_REFERENCE), self.KBOT_REFERENCE)

    def test_safeencrypt_invalid_wrong_password_does_not_verify(self) -> None:
        assert compare("ne", safe_encrypt("wrong", self.KBOT_REFERENCE), self.KBOT_REFERENCE)

    def test_safeencrypt_valid_uses_random_salt(self) -> None:
        assert compare("ne", safe_encrypt("K0nversOK!"), safe_encrypt("K0nversOK!"))


class TestSetAdminPassword:
    """Tests for set_admin_password."""

    def test_setadminpassword_valid_stores_hashed_password_with_parameterized_query(
        self, settings: DbSettings, mock_conn: MagicMock
    ) -> None:
        set_admin_password(settings, "new-pwd")

        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0]
        assert compare("in", "users_im_account", args[0])
        (stored,) = args[1]
        assert compare("ne", stored, "new-pwd")
        assert compare("eq", safe_encrypt("new-pwd", stored), stored)
        mock_conn.commit.assert_called_once()

    def test_setadminpassword_invalid_raises_when_admin_account_is_missing(
        self, settings: DbSettings, mock_conn: MagicMock
    ) -> None:
        """No updated row means the users load did not create 'admin': fail instead of committing."""
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.rowcount = 0

        with pytest.raises(RuntimeError, match="No 'admin' account"):
            set_admin_password(settings, "new-pwd")

        mock_conn.commit.assert_not_called()
