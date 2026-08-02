"""Tests for database.external_database module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from database.base import ExternalDbSettings
from database.external_database import ExternalDatabase


@pytest.fixture
def settings(tmp_path: Path) -> ExternalDbSettings:
    return ExternalDbSettings(
        database="db",
        user="user",
        password="password",
        schema_paths=[tmp_path / "schema.sql"],
    )


@pytest.fixture
def db(settings: ExternalDbSettings) -> ExternalDatabase:
    return ExternalDatabase(settings)


class TestPrepare:
    """Test cases for ExternalDatabase.prepare."""

    def test_prepare_valid_checks_connection(self, db: ExternalDatabase) -> None:
        with patch.object(db, "check_connection") as mock_check:
            db.prepare()

            mock_check.assert_called_once_with()


class TestCheckConnection:
    """Test cases for ExternalDatabase.check_connection."""

    def test_checkconnection_valid_opens_and_closes_connection(
        self, db: ExternalDatabase, settings: ExternalDbSettings
    ) -> None:
        with patch("database.external_database.connect") as mock_connect:
            db.check_connection()

            mock_connect.assert_called_once_with(settings)
            mock_connect.return_value.__enter__.assert_called_once()
            mock_connect.return_value.__exit__.assert_called_once()


class TestCheckIsEmpty:
    """Test cases for ExternalDatabase._check_is_empty."""

    def test_checkisempty_valid_returns_true_when_empty_and_allowed(
        self, db: ExternalDatabase
    ) -> None:
        db._ExternalDatabase__settings.allow_schema_creation = True

        with patch("database.external_database.is_database_empty", return_value=True):
            assert db._check_is_empty() is True

    def test_checkisempty_valid_returns_false_when_not_empty(
        self, db: ExternalDatabase
    ) -> None:
        with patch("database.external_database.is_database_empty", return_value=False):
            assert db._check_is_empty() is False

    def test_checkisempty_invalid_raises_when_empty_and_not_allowed(
        self, db: ExternalDatabase
    ) -> None:
        with (
            patch("database.external_database.is_database_empty", return_value=True),
            pytest.raises(RuntimeError, match="schema creation"),
        ):
            db._check_is_empty()


class TestInitialize:
    """Test cases for ExternalDatabase.initialize."""

    def test_initialize_valid_applies_schema_when_empty(self, db: ExternalDatabase) -> None:
        with (
            patch.object(db, "_check_is_empty", return_value=True),
            patch("database.external_database.apply_schema") as mock_apply_schema,
        ):
            db.initialize()

            mock_apply_schema.assert_called_once()

    def test_initialize_valid_skips_schema_when_not_empty(self, db: ExternalDatabase) -> None:
        with (
            patch.object(db, "_check_is_empty", return_value=False),
            patch("database.external_database.apply_schema") as mock_apply_schema,
        ):
            db.initialize()

            mock_apply_schema.assert_not_called()


class TestUpgrade:
    """Test cases for ExternalDatabase.upgrade."""

    def test_upgrade_valid_applies_upgrades_when_not_empty(
        self, db: ExternalDatabase
    ) -> None:
        with (
            patch.object(db, "_check_is_empty", return_value=False),
            patch("database.external_database.apply_missing_upgrades") as mock_upgrade,
        ):
            db.upgrade()

            mock_upgrade.assert_called_once()

    def test_upgrade_valid_skips_upgrades_when_empty(self, db: ExternalDatabase) -> None:
        with (
            patch.object(db, "_check_is_empty", return_value=True),
            patch("database.external_database.apply_missing_upgrades") as mock_upgrade,
        ):
            db.upgrade()

            mock_upgrade.assert_not_called()
