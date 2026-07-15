"""Installable package for workarea installation.

This package exposes ``WorkareaInstallable``, the only concrete installable,
through the ``create_installable`` factory. Product and bundle downloads live
in the ``downloadable`` package.
"""

from installable.factory import create_installable
from installable.base import InstallableBase

__all__ = [
    "InstallableBase",
    "create_installable",
]
