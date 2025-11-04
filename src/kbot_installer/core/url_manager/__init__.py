"""URL management package for building and manipulating URLs.

This package provides a base URL manager interface and concrete implementations
for different URL manipulation libraries.
"""

from kbot_installer.core.url_manager.factory import create_url_manager
from kbot_installer.core.url_manager.url_manager_base import URLManagerBase

__all__ = ["URLManagerBase", "create_url_manager"]
