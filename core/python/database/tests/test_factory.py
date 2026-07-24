"""Tests for database.factory module."""

from unittest.mock import MagicMock, patch

import pytest

import database.factory as factory_module
from database.base import DatabaseBackend, DbSettings
from database.factory import add_db, add_settings
from utils.utils_for_unit_tests import compare


class TestAddSettings:
    """Test cases for add_settings."""

    def test_addsettings_valid_delegates_to_factory(self) -> None:
        with patch("database.factory.factory_method") as mock_factory_method:
            mock_settings = MagicMock(spec=DbSettings)
            mock_factory_method.return_value = mock_settings

            result = add_settings("internal", database="db")

            mock_factory_method.assert_called_once_with(
                name="internal",
                package="database",
                database="db",
            )
            assert compare("eq", result, mock_settings)

    def test_addsettings_invalid_raises_when_package_is_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(factory_module, "__package__", None)

        with pytest.raises(RuntimeError, match="package cannot be None"):
            add_settings("internal")

    @pytest.mark.parametrize(
        "exception",
        [
            ImportError("Cannot import module"),
            AttributeError("Class not found"),
        ],
    )
    def test_addsettings_invalid_propagates_factory_errors(
        self, exception: BaseException
    ) -> None:
        with patch("database.factory.factory_method") as mock_factory_method:
            mock_factory_method.side_effect = exception

            with pytest.raises(type(exception), match=str(exception)):
                add_settings("external")


class TestAddDb:
    """Test cases for add_db."""

    def test_adddb_valid_builds_settings_then_backend(self) -> None:
        mock_settings = MagicMock(spec=DbSettings)
        mock_backend = MagicMock(spec=DatabaseBackend)

        with patch("database.factory.factory_method") as mock_factory_method:
            mock_factory_method.side_effect = [mock_settings, mock_backend]

            result = add_db("internal", database="db")

            assert compare(
                "eq",
                mock_factory_method.call_args_list[0].kwargs,
                {"name": "internal", "package": "database", "database": "db"},
            )
            assert compare(
                "eq",
                mock_factory_method.call_args_list[1].kwargs,
                {"name": "internal", "package": "database", "settings": mock_settings},
            )
            assert compare("eq", result, mock_backend)

    def test_adddb_invalid_raises_when_package_is_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(factory_module, "__package__", None)

        with pytest.raises(RuntimeError, match="package cannot be None"):
            add_db("internal")
