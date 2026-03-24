"""Setup managers for configuring kbot workarea."""

from kbot_installer.core.setup.base import BaseSetupManager
from kbot_installer.core.setup.database_setup import (
    ExternalDatabaseSetupManager,
    InternalDatabaseSetupManager,
)
from kbot_installer.core.setup.docs_setup import PythonDocsSetupManager

__all__ = [
    "BaseSetupManager",
    "ExternalDatabaseSetupManager",
    "InternalDatabaseSetupManager",
    "PythonDocsSetupManager",
]
