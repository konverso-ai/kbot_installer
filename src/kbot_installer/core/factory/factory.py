"""Factory functions for dynamic class and method instantiation.

This module provides utilities for dynamically creating classes, objects,
and calling methods using string names and importlib.
"""

import importlib
from typing import TypeVar

from kbot_installer.core.factory.utils import build_class_name, build_module_name

T = TypeVar("T")


def factory_class(name: str, package: str) -> type[T]:
    """Get a class by name from a package using generic naming convention.

    Args:
        name: Base name of the class (e.g., "nexus", "github").
        package: Package name where the class is located.

    Returns:
        The class object.

    Raises:
        ImportError: If the package or module cannot be imported.
        AttributeError: If the class is not found in the package.

    Example:
        >>> NexusProvider = factory_class("nexus", "kbot_installer.core.provider")
        >>> print(NexusProvider)
        <class 'provider.nexus_provider.NexusProvider'>

        >>> GithubVersioner = factory_class("github", "versioner")
        >>> print(GithubVersioner)
        <class 'versioner.github_versioner.GithubVersioner'>

    """
    # Build module and class names using utility functions
    module_name = build_module_name(name, package)
    class_name = build_class_name(name, package)

    # Import the specific module
    module = importlib.import_module(f"{package}.{module_name}")

    # Get the class from the module
    return getattr(module, class_name)


def factory_object(name: str, package: str, **kwargs: object) -> T:
    """Create an instance of a class by name from a package using generic naming convention.

    Args:
        name: Base name of the class (e.g., "nexus", "github").
        package: Package name where the class is located.
        **kwargs: Keyword arguments to pass to the class constructor.

    Returns:
        An instance of the specified class.

    Raises:
        ImportError: If the package or module cannot be imported.
        AttributeError: If the class is not found in the package.
        TypeError: If the class cannot be instantiated with the provided arguments.

    Example:
        >>> nexus = factory_object("nexus", "provider", base_url="https://nexus.example.com")
        >>> print(nexus)
        NexusProvider(https://nexus.example.com)

        >>> github = factory_object("github", "versioner", token="test_token")
        >>> print(github)
        GitHubVersioner(https://github.com)

    """
    cls = factory_class(name, package)
    return cls(**kwargs)


def factory_method(name: str, package: str, **kwargs: object) -> object:
    """Call a method or function by name from a package using generic naming convention.

    This function is a convenience wrapper around factory_class that:
    1. Gets the class using factory_class(name, package)
    2. Instantiates the class with the provided arguments

    Args:
        name: Base name of the class (e.g., "nexus", "github").
        package: Package name where the class is located.
        **kwargs: Keyword arguments to pass to the class constructor.

    Returns:
        An instance of the specified class.

    Raises:
        ImportError: If the package or module cannot be imported.
        AttributeError: If the class is not found.
        TypeError: If the class cannot be instantiated with the provided arguments.

    Example:
        >>> nexus = factory_method("nexus", "provider", base_url="https://nexus.example.com")
        >>> print(nexus)
        NexusProvider(https://nexus.example.com)

        >>> github = factory_method("github", "versioner", token="test_token")
        >>> print(github)
        GitHubVersioner(https://github.com)

    """
    # Get the class using factory_class
    cls = factory_class(name, package)

    # Instantiate and return the class
    return cls(**kwargs)
