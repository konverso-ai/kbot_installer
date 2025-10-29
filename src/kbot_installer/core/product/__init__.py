"""Product package for managing product definitions and dependencies.

This package provides functionality to load, manage, and visualize product
definitions from XML and JSON files, including dependency graph analysis.
"""

from kbot_installer.core.product.dependency_graph import DependencyGraph
from kbot_installer.core.product.factory import create_installable
from kbot_installer.core.product.installable_base import InstallableBase
from kbot_installer.core.product.product_collection import ProductCollection
from kbot_installer.core.product.renderer import DependencyTreeRenderer

__all__ = [
    "DependencyGraph",
    "DependencyTreeRenderer",
    "InstallableBase",
    "ProductCollection",
    "create_installable",
]
