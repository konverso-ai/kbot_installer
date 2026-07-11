from typing import Literal, cast

from database.base import DatabaseBackend, DbSettings
from utils.factory.factory import factory_method

DbMode = Literal["internal", "external"]


def add_settings(mode: DbMode, **kwargs) -> DbSettings:
    if (package := __package__) is None:
        msg = "package cannot be None or empty."
        raise RuntimeError(msg)

    return cast(
        DbSettings,
        factory_method(
            name=mode,
            package=package,
            **kwargs,
        ),
    )


def add_db(mode: DbMode, **kwargs) -> DatabaseBackend:
    settings = add_settings(mode=mode, **kwargs)
    if (package := __package__) is None:
        msg = "package cannot be None or empty."
        raise RuntimeError(msg)
    return cast(
        DatabaseBackend,
        factory_method(
            name=mode,
            package=package,
            settings=settings,
        ),
    )
