"""Factory functions for database settings and backend instances."""

from typing import Literal, cast

from database.base import DatabaseBackend, DbSettings
from utils.factory.factory import factory_method

DbMode = Literal["internal", "external"]


def add_settings(mode: DbMode, **kwargs) -> DbSettings:
    """Create the settings instance matching the given database mode.

    Args:
        mode: Database mode, either ``"internal"`` or ``"external"``.
        **kwargs: Keyword arguments passed to the settings constructor.

    Returns:
        The settings instance for the requested mode.

    Raises:
        RuntimeError: If the current package cannot be resolved.

    """
    if (package := __package__) is None:
        msg = "package cannot be None or empty."
        raise RuntimeError(msg)

    return cast(
        "DbSettings",
        factory_method(
            name=mode,
            package=package,
            **kwargs,
        ),
    )


def add_db(mode: DbMode, **kwargs) -> DatabaseBackend:
    """Create the database backend instance matching the given mode.

    Args:
        mode: Database mode, either ``"internal"`` or ``"external"``.
        **kwargs: Keyword arguments passed to the settings constructor.

    Returns:
        The database backend instance for the requested mode.

    Raises:
        RuntimeError: If the current package cannot be resolved.

    """
    settings = add_settings(mode=mode, **kwargs)
    if (package := __package__) is None:
        msg = "package cannot be None or empty."
        raise RuntimeError(msg)
    return cast(
        "DatabaseBackend",
        factory_method(
            name=mode,
            package=package,
            settings=settings,
        ),
    )
