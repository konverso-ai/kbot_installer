"""Tests for database.postgres_cluster module."""

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from database import postgres_cluster
from database.base import InternalDbSettings
from utils.utils_for_unit_tests import compare


@pytest.fixture
def settings(tmp_path: Path) -> InternalDbSettings:
    return InternalDbSettings(
        database="db",
        user="user",
        password="password",
        schema_path=tmp_path / "schema.sql",
        pg_dir=tmp_path / "pg",
        pg_data=tmp_path / "pg" / "data",
        log_path=tmp_path / "pg" / "logs" / "postgres.log",
        admin_password="admin",
    )


class TestIsInitialized:
    """Test cases for is_initialized."""

    def test_isinitialized_valid_returns_true_when_pgversion_exists(
        self, settings: InternalDbSettings
    ) -> None:
        settings.pg_data.mkdir(parents=True)
        (settings.pg_data / "PG_VERSION").write_text("16")

        assert postgres_cluster.is_initialized(settings) is True

    def test_isinitialized_valid_returns_false_when_missing(
        self, settings: InternalDbSettings
    ) -> None:
        assert postgres_cluster.is_initialized(settings) is False


class TestInitdb:
    """Test cases for initdb."""

    def test_initdb_valid_calls_pgctl_with_encoding_and_locale(
        self, settings: InternalDbSettings
    ) -> None:
        with patch("database.postgres_cluster.subprocess.run") as mock_run:
            mock_run.return_value = CompletedProcess(args=[], returncode=0)

            postgres_cluster.initdb(settings)

            called_args = mock_run.call_args.args[0]
            assert compare("in", str(settings.pg_bin / "pg_ctl"), called_args)
            assert compare("in", f"-E {settings.encoding}", called_args)
            assert compare("in", f"--locale={settings.locale}", called_args)

    def test_initdb_invalid_raises_when_pgctl_fails(
        self, settings: InternalDbSettings
    ) -> None:
        with patch("database.postgres_cluster.subprocess.run") as mock_run:
            mock_run.return_value = CompletedProcess(
                args=[], returncode=1, stderr=b"boom"
            )

            with pytest.raises(postgres_cluster.PostgresClusterError, match="boom"):
                postgres_cluster.initdb(settings)


class TestIsRunning:
    """Test cases for is_running."""

    def test_isrunning_valid_returns_true_on_zero_returncode(
        self, settings: InternalDbSettings
    ) -> None:
        with patch("database.postgres_cluster.subprocess.run") as mock_run:
            mock_run.return_value = CompletedProcess(args=[], returncode=0)

            assert postgres_cluster.is_running(settings) is True

    def test_isrunning_valid_returns_false_on_nonzero_returncode(
        self, settings: InternalDbSettings
    ) -> None:
        with patch("database.postgres_cluster.subprocess.run") as mock_run:
            mock_run.return_value = CompletedProcess(args=[], returncode=1)

            assert postgres_cluster.is_running(settings) is False


class TestStart:
    """Test cases for start."""

    def test_start_valid_raises_when_not_running_afterward(
        self, settings: InternalDbSettings
    ) -> None:
        with (
            patch("database.postgres_cluster.subprocess.run") as mock_run,
            patch("database.postgres_cluster.is_running", return_value=False),
        ):
            mock_run.return_value = CompletedProcess(args=[], returncode=1)

            with pytest.raises(postgres_cluster.PostgresClusterError):
                postgres_cluster.start(settings)

    def test_start_valid_succeeds_when_running_afterward(
        self, settings: InternalDbSettings
    ) -> None:
        with (
            patch("database.postgres_cluster.subprocess.run") as mock_run,
            patch("database.postgres_cluster.is_running", return_value=True),
        ):
            mock_run.return_value = CompletedProcess(args=[], returncode=0)

            postgres_cluster.start(settings)

            called_args = mock_run.call_args.args[0]
            assert compare("in", f"-p{settings.port}", called_args)

    def test_start_valid_includes_socket_dir_option_when_set(
        self, settings: InternalDbSettings
    ) -> None:
        settings.socket_dir = settings.pg_data.parent / "run"

        with (
            patch("database.postgres_cluster.subprocess.run") as mock_run,
            patch("database.postgres_cluster.is_running", return_value=True),
        ):
            mock_run.return_value = CompletedProcess(args=[], returncode=0)

            postgres_cluster.start(settings)

            called_args = mock_run.call_args.args[0]
            assert compare("in", f"-k{settings.socket_dir}", called_args)
            assert compare("eq", settings.socket_dir.is_dir(), True)  # noqa: FBT003


class TestStop:
    """Test cases for stop."""

    def test_stop_valid_calls_pgctl_stop(self, settings: InternalDbSettings) -> None:
        with patch("database.postgres_cluster.subprocess.run") as mock_run:
            postgres_cluster.stop(settings)

            called_args = mock_run.call_args.args[0]
            assert compare("in", "stop", called_args)
            assert compare("in", str(settings.pg_data), called_args)


class TestEnsureRunning:
    """Test cases for ensure_running."""

    def test_ensurerunning_valid_initializes_when_missing(
        self, settings: InternalDbSettings
    ) -> None:
        with (
            patch(
                "database.postgres_cluster.is_initialized", return_value=False
            ),
            patch("database.postgres_cluster.initdb") as mock_initdb,
            patch("database.postgres_cluster.is_running", return_value=True),
            patch("database.postgres_cluster.start") as mock_start,
        ):
            postgres_cluster.ensure_running(settings)

            mock_initdb.assert_called_once_with(settings)
            mock_start.assert_not_called()

    def test_ensurerunning_valid_starts_when_not_running(
        self, settings: InternalDbSettings
    ) -> None:
        with (
            patch("database.postgres_cluster.is_initialized", return_value=True),
            patch("database.postgres_cluster.initdb") as mock_initdb,
            patch("database.postgres_cluster.is_running", return_value=False),
            patch("database.postgres_cluster.start") as mock_start,
        ):
            postgres_cluster.ensure_running(settings)

            mock_initdb.assert_not_called()
            mock_start.assert_called_once_with(settings)

    def test_ensurerunning_valid_does_nothing_when_already_running(
        self, settings: InternalDbSettings
    ) -> None:
        with (
            patch("database.postgres_cluster.is_initialized", return_value=True),
            patch("database.postgres_cluster.initdb") as mock_initdb,
            patch("database.postgres_cluster.is_running", return_value=True),
            patch("database.postgres_cluster.start") as mock_start,
        ):
            postgres_cluster.ensure_running(settings)

            mock_initdb.assert_not_called()
            mock_start.assert_not_called()
