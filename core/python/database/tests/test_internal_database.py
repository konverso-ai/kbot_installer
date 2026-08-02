"""Tests for database.internal_database module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from database.base import InternalDbSettings
from database.internal_database import InternalDatabase
from utils.utils_for_unit_tests import compare


@pytest.fixture
def settings(tmp_path: Path) -> InternalDbSettings:
    return InternalDbSettings(
        database="db",
        user="user",
        password="password",
        schema_paths=[tmp_path / "schema.sql"],
        pg_dir=tmp_path / "pg",
        pg_data=tmp_path / "pg" / "data",
        log_path=tmp_path / "pg" / "logs" / "postgres.log",
        admin_password="admin",
    )


@pytest.fixture
def db(settings: InternalDbSettings) -> InternalDatabase:
    return InternalDatabase(settings)


@pytest.fixture
def mock_conn() -> MagicMock:
    with patch("database.internal_database.psycopg.connect") as mock_connect:
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        mock_connect.return_value.__enter__.return_value = conn
        yield conn


class TestPrepare:
    """Test cases for InternalDatabase.prepare."""

    def test_prepare_valid_bootstraps_cluster_role_and_database(
        self, db: InternalDatabase, settings: InternalDbSettings
    ) -> None:
        with (
            patch("database.internal_database.postgres_cluster.ensure_running") as mock_run,
            patch.object(db, "_create_role_if_missing") as mock_role,
            patch.object(db, "_create_database_if_missing") as mock_database,
        ):
            db.prepare()

            mock_run.assert_called_once_with(settings)
            mock_role.assert_called_once_with()
            mock_database.assert_called_once_with()


class TestCheckConnection:
    """Test cases for InternalDatabase.check_connection."""

    def test_checkconnection_valid_opens_and_closes_connection(
        self, db: InternalDatabase, settings: InternalDbSettings
    ) -> None:
        with patch("database.internal_database.connect") as mock_connect:
            db.check_connection()

            mock_connect.assert_called_once_with(settings)
            mock_connect.return_value.__enter__.assert_called_once()
            mock_connect.return_value.__exit__.assert_called_once()


class TestInitialize:
    """Test cases for InternalDatabase.initialize."""

    def test_initialize_valid_applies_schema_when_empty(self, db: InternalDatabase) -> None:
        with (
            patch("database.internal_database.is_database_empty", return_value=True),
            patch("database.internal_database.apply_schema") as mock_apply_schema,
        ):
            db.initialize()

            mock_apply_schema.assert_called_once()

    def test_initialize_valid_skips_schema_when_not_empty(self, db: InternalDatabase) -> None:
        with (
            patch("database.internal_database.is_database_empty", return_value=False),
            patch("database.internal_database.apply_schema") as mock_apply_schema,
        ):
            db.initialize()

            mock_apply_schema.assert_not_called()


class TestUpgrade:
    """Test cases for InternalDatabase.upgrade."""

    def test_upgrade_valid_applies_upgrades_when_not_empty(
        self, db: InternalDatabase
    ) -> None:
        with (
            patch("database.internal_database.is_database_empty", return_value=False),
            patch("database.internal_database.apply_missing_upgrades") as mock_upgrade,
        ):
            db.upgrade()

            mock_upgrade.assert_called_once()

    def test_upgrade_valid_skips_upgrades_when_empty(self, db: InternalDatabase) -> None:
        with (
            patch("database.internal_database.is_database_empty", return_value=True),
            patch("database.internal_database.apply_missing_upgrades") as mock_upgrade,
        ):
            db.upgrade()

            mock_upgrade.assert_not_called()


class TestAdminConnect:
    """Test cases for InternalDatabase._admin_connect."""

    def test_adminconnect_valid_connects_to_admin_database_by_default(
        self, db: InternalDatabase, settings: InternalDbSettings
    ) -> None:
        with patch("database.internal_database.psycopg.connect") as mock_connect:
            db._admin_connect()

            mock_connect.assert_called_once_with(
                host=settings.host,
                port=settings.port,
                dbname=settings.admin_database,
                user=settings.admin_user,
                password=settings.admin_password,
            )
            assert compare("eq", mock_connect.return_value.autocommit, True)  # noqa: FBT003

    def test_adminconnect_valid_connects_to_given_database_when_specified(
        self, db: InternalDatabase
    ) -> None:
        with patch("database.internal_database.psycopg.connect") as mock_connect:
            db._admin_connect(database="other")

            assert compare("eq", mock_connect.call_args.kwargs["dbname"], "other")


class TestCreateRoleIfMissing:
    """Test cases for InternalDatabase._create_role_if_missing."""

    def test_createroleifmissing_valid_skips_creation_when_exists(
        self, db: InternalDatabase, mock_conn: MagicMock
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (1,)

        db._create_role_if_missing()

        assert compare("eq", cur.execute.call_count, 1)

    def test_createroleifmissing_valid_creates_role_when_missing(
        self, db: InternalDatabase, mock_conn: MagicMock, settings: InternalDbSettings
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = None

        db._create_role_if_missing()

        assert compare("eq", cur.execute.call_count, 2)
        create_call = cur.execute.call_args_list[1]
        create_sql = str(create_call.args[0])
        assert compare("eq", len(create_call.args), 1)
        assert compare("in", settings.user, create_sql)
        assert compare("in", settings.password, create_sql)


class TestCreateDatabaseIfMissing:
    """Test cases for InternalDatabase._create_database_if_missing."""

    def test_createdatabaseifmissing_valid_connects_with_admin_credentials(
        self, db: InternalDatabase, settings: InternalDbSettings
    ) -> None:
        with patch("database.internal_database.psycopg.connect") as mock_connect:
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchone.return_value = (1,)
            conn.cursor.return_value.__enter__.return_value = cur
            mock_connect.return_value.__enter__.return_value = conn

            db._create_database_if_missing()

            mock_connect.assert_called_once_with(
                host=settings.host,
                port=settings.port,
                dbname=settings.admin_database,
                user=settings.admin_user,
                password=settings.admin_password,
            )

    def test_createdatabaseifmissing_valid_skips_creation_when_exists(
        self, db: InternalDatabase, mock_conn: MagicMock
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = (1,)

        with patch.object(db, "_configure_new_database") as mock_configure:
            db._create_database_if_missing()

            assert compare("eq", cur.execute.call_count, 1)
            mock_configure.assert_not_called()

    def test_createdatabaseifmissing_valid_creates_database_when_missing(
        self, db: InternalDatabase, mock_conn: MagicMock, settings: InternalDbSettings
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = None

        with patch.object(db, "_configure_new_database") as mock_configure:
            db._create_database_if_missing()

            assert compare("eq", cur.execute.call_count, 2)
            create_sql = str(cur.execute.call_args_list[1].args[0])
            assert compare("in", settings.database, create_sql)
            assert compare("in", settings.template, create_sql)
            assert compare("in", settings.user, create_sql)
            mock_configure.assert_called_once_with()


class TestConfigureNewDatabase:
    """Test cases for InternalDatabase._configure_new_database."""

    def test_configurenewdatabase_valid_sets_schema_owner_only_by_default(
        self, db: InternalDatabase, mock_conn: MagicMock, settings: InternalDbSettings
    ) -> None:
        cur = mock_conn.cursor.return_value.__enter__.return_value

        db._configure_new_database()

        assert compare("eq", cur.execute.call_count, 1)
        owner_sql = str(cur.execute.call_args_list[0].args[0])
        assert compare("in", settings.user, owner_sql)

    def test_configurenewdatabase_valid_sets_max_connections_when_configured(
        self, db: InternalDatabase, mock_conn: MagicMock, settings: InternalDbSettings
    ) -> None:
        settings.max_connections = 512
        cur = mock_conn.cursor.return_value.__enter__.return_value

        db._configure_new_database()

        assert compare("eq", cur.execute.call_count, 2)
        max_conn_call = cur.execute.call_args_list[1]
        max_conn_sql = str(max_conn_call.args[0])
        assert compare("eq", len(max_conn_call.args), 1)
        assert compare("in", "max_connections", max_conn_sql)
        assert compare("in", "512", max_conn_sql)
