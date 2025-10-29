"""Interactive prompters for installation parameters."""

from kbot_installer.core.interactivity.admin_prompter import AdminPrompter
from kbot_installer.core.interactivity.base import InteractivePrompter
from kbot_installer.core.interactivity.database_prompter import DatabasePrompter
from kbot_installer.core.interactivity.http_prompter import HttpPrompter
from kbot_installer.core.interactivity.license_prompter import LicensePrompter
from kbot_installer.core.interactivity.redis_prompter import RedisPrompter

__all__ = [
    "AdminPrompter",
    "DatabasePrompter",
    "HttpPrompter",
    "InteractivePrompter",
    "LicensePrompter",
    "RedisPrompter",
]
