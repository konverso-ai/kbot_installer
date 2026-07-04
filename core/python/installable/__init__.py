"""Installable package for managing installable definitions and dependencies.

This package provides functionality to load, manage, and visualize installable
definitions from XML and JSON files, including dependency graph analysis.
"""

from installable.factory import create_installable
from installable.base import InstallableBase

__all__ = [
    "InstallableBase",
    "create_installable",
]
