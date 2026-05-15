"""Setup managers for configuring kbot workarea."""

from setup.base import BaseSetupManager
from setup.database_setup import (
    ExternalDatabaseSetupManager,
    InternalDatabaseSetupManager,
)
from setup.docs_setup import PythonDocsSetupManager

__all__ = [
    "BaseSetupManager",
    "ExternalDatabaseSetupManager",
    "InternalDatabaseSetupManager",
    "PythonDocsSetupManager",
]
