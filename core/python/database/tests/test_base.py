"""Tests for database.base module."""

from pathlib import Path

import pytest

from database.base import DbSettings, ExternalDbSettings, InternalDbSettings
from utils.utils_for_unit_tests import compare


def _base_kwargs(**overrides: object) -> dict:
    kwargs = {
        "database": "db",
        "user": "user",
        "password": "password",
        "schema_path": Path("/schema.sql"),
    }
    kwargs.update(overrides)
    return kwargs


def _internal_kwargs(**overrides: object) -> dict:
    kwargs = {
        **_base_kwargs(),
        "admin_password": "admin",
        "pg_dir": Path("/pg"),
        "pg_data": Path("/pg/data"),
        "log_path": Path("/pg/logs/postgres.log"),
    }
    kwargs.update(overrides)
    return kwargs


class TestDbSettings:
    """Test cases for DbSettings."""

    def test_dbsettings_valid_uses_defaults(self) -> None:
        settings = DbSettings(**_base_kwargs())

        assert compare("eq", settings.host, "localhost")
        assert compare("eq", settings.port, 5432)
        assert compare("eq", settings.upgrades_dir, None)
        assert compare("eq", settings.target_version, None)

    def test_dbsettings_valid_overrides_defaults(self) -> None:
        settings = DbSettings(
            **_base_kwargs(
                host="db.example.com",
                port=6543,
                upgrades_dir=Path("/upgrades"),
                target_version="1.0.0",
            )
        )

        assert compare("eq", settings.host, "db.example.com")
        assert compare("eq", settings.port, 6543)
        assert compare("eq", settings.upgrades_dir, Path("/upgrades"))
        assert compare("eq", settings.target_version, "1.0.0")

    def test_dbsettings_invalid_raises_on_missing_required_field(self) -> None:
        kwargs = _base_kwargs()
        del kwargs["database"]

        with pytest.raises(Exception):  # noqa: PT011, B017 - pydantic ValidationError
            DbSettings(**kwargs)


class TestInternalDbSettings:
    """Test cases for InternalDbSettings."""

    def test_internaldbsettings_valid_uses_defaults(self) -> None:
        settings = InternalDbSettings(**_internal_kwargs())

        assert compare("eq", settings.admin_database, "postgres")
        assert compare("eq", settings.admin_user, "postgres")
        assert compare("eq", settings.admin_password, "admin")
        assert compare("eq", settings.template, "template0")
        assert compare("eq", settings.socket_dir, None)
        assert compare("eq", settings.encoding, "UTF8")
        assert compare("eq", settings.locale, "en_US.utf8")
        assert compare("eq", settings.max_connections, None)

    def test_internaldbsettings_valid_overrides_defaults(self) -> None:
        settings = InternalDbSettings(
            **_internal_kwargs(
                admin_database="admin_db",
                admin_user="root",
                admin_password="secret",
                template="template1",
                socket_dir=Path("/pg/run"),
                encoding="LATIN1",
                locale="fr_FR.utf8",
                max_connections=512,
            )
        )

        assert compare("eq", settings.admin_database, "admin_db")
        assert compare("eq", settings.admin_user, "root")
        assert compare("eq", settings.admin_password, "secret")
        assert compare("eq", settings.template, "template1")
        assert compare("eq", settings.socket_dir, Path("/pg/run"))
        assert compare("eq", settings.encoding, "LATIN1")
        assert compare("eq", settings.locale, "fr_FR.utf8")
        assert compare("eq", settings.max_connections, 512)

    def test_internaldbsettings_invalid_raises_on_missing_admin_password(self) -> None:
        kwargs = _internal_kwargs()
        del kwargs["admin_password"]

        with pytest.raises(Exception):  # noqa: PT011, B017 - pydantic ValidationError
            InternalDbSettings(**kwargs)

    def test_pgbin_valid_joins_pgdir(self) -> None:
        settings = InternalDbSettings(
            **_internal_kwargs(pg_dir=Path("/opt/postgres"))
        )

        assert compare("eq", settings.pg_bin, Path("/opt/postgres/bin"))


class TestExternalDbSettings:
    """Test cases for ExternalDbSettings."""

    def test_externaldbsettings_valid_defaults_schema_creation_to_false(self) -> None:
        settings = ExternalDbSettings(**_base_kwargs())

        assert compare("eq", settings.allow_schema_creation, False)  # noqa: FBT003

    def test_externaldbsettings_valid_allows_schema_creation_override(self) -> None:
        settings = ExternalDbSettings(**_base_kwargs(allow_schema_creation=True))

        assert compare("eq", settings.allow_schema_creation, True)  # noqa: FBT003
