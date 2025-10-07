"""Factory package for dynamic class and method instantiation.

This package provides utilities for dynamically creating classes, objects,
and calling methods using string names and importlib.
"""

from kbot_installer.core.factory.factory import (
    factory_class,
    factory_method,
    factory_object,
)

__all__ = [
    "factory_class",
    "factory_method",
    "factory_object",
]
