"""Factory functions for dynamic class and method instantiation.

This module provides utilities for dynamically creating classes, objects,
and calling methods using string names and importlib.
"""

import importlib
from typing import TypeVar

from .utils import build_class_name, build_module_name

T = TypeVar("T")


def factory_class(name: str, package: str) -> type[T]:
    """Get a class by name from a package using generic naming convention.

    Builds the module and class names from `name`/`package` using the
    `{name}_{package}` / `{Name}{Package}` convention, then delegates the actual
    import + attribute lookup to `factory_function`.

    Args:
        name: Base name of the class (e.g., "nexus", "github").
        package: Package name where the class is located.

    Returns:
        The class object.

    Raises:
        ImportError: If the package or module cannot be imported.
        AttributeError: If the class is not found in the package.

    Example:
        >>> NexusProvider = factory_class("nexus", "provider")
        >>> print(NexusProvider)
        <class 'provider.nexus_provider.NexusProvider'>

        >>> GithubVersioner = factory_class("github", "versioner")
        >>> print(GithubVersioner)
        <class 'versioner.github_versioner.GithubVersioner'>

    """
    # Build module and class names using the naming convention utility functions
    module_name = build_module_name(name, package)
    class_name = build_class_name(name, package)

    # Delegate the actual import + attribute lookup to factory_function
    return factory_function(f"{package}.{module_name}", class_name)


def factory_function(module_name: str, attribute_name: str) -> T:
    """Get an attribute (class, function, or object) from an explicit module path.

    Unlike `factory_class`, this function does not impose any naming convention
    between the module and the attribute name: it simply performs
    `importlib.import_module(module_name)` followed by `getattr(module, attribute_name)`.
    Use this when the module/class names don't follow the `{name}_{package}` /
    `{Name}{Package}` convention expected by `factory_class`.

    Args:
        module_name: Fully qualified module path to import (e.g. "provider.github_provider").
        attribute_name: Name of the attribute to retrieve from the imported module
            (e.g. "GithubProvider").

    Returns:
        The attribute object (class, function, or any other module-level object).

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the attribute is not found in the module.

    Example:
        >>> NexusProvider = factory_function("provider.nexus_provider", "NexusProvider")
        >>> print(NexusProvider)
        <class 'provider.nexus_provider.NexusProvider'>

        >>> build_url = factory_function("provider.utils", "build_url")
        >>> print(build_url)
        <function build_url at 0x...>

    """
    module = importlib.import_module(module_name)
    return getattr(module, attribute_name)


def factory_object(name: str, package: str, **kwargs: object) -> T:
    """Create an instance of a class by name from a package using generic naming convention.

    Builds the module and class names from the naming convention (like `factory_class`
    does), then delegates the actual import + attribute lookup to `factory_function`
    before instantiating the resulting class.

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
    # Build module and class names using the naming convention utility functions
    module_name = build_module_name(name, package)
    class_name = build_class_name(name, package)

    # Delegate the actual import + attribute lookup to factory_function
    cls = factory_function(f"{package}.{module_name}", class_name)
    return cls(**kwargs)


def factory_method(name: str, package: str, **kwargs: object) -> object:
    """Create an instance of a class by name from a package using generic naming convention.

    This is a convenience alias kept for backward compatibility: it behaves exactly like
    `factory_object` and simply delegates to it.

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
    return factory_object(name, package, **kwargs)
