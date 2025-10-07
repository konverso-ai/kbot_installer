"""Utility functions for the factory package.

This module provides utility functions for string conversion and naming conventions.
"""


def snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case string to PascalCase.

    Args:
        snake_str: String in snake_case format.

    Returns:
        String converted to PascalCase.

    Example:
        >>> snake_to_pascal("nexus_provider")
        "NexusProvider"
        >>> snake_to_pascal("github_versioner")
        "GithubVersioner"
        >>> snake_to_pascal("bitbucket_versioner")
        "BitbucketVersioner"

    """
    return "".join(word.capitalize() for word in snake_str.split("_"))


def build_module_name(name: str, package: str) -> str:
    """Build module name from name and package.

    Args:
        name: Base name (e.g., "nexus", "github").
        package: Package name (e.g., "provider", "versioner", "auth.pygit_authentication").

    Returns:
        Module name in snake_case format.

    Example:
        >>> build_module_name("nexus", "provider")
        "nexus_provider"
        >>> build_module_name("github", "versioner")
        "github_versioner"
        >>> build_module_name("key_pair", "auth.pygit_authentication")
        "key_pair_pygit_authentication"

    """
    # Extract the rightmost part after the last dot for nested packages
    package_name = package.split(".")[-1]
    return f"{name}_{package_name}"


def build_class_name(name: str, package: str) -> str:
    """Build class name from name and package.

    Args:
        name: Base name (e.g., "nexus", "github").
        package: Package name (e.g., "provider", "versioner", "auth.pygit_authentication").

    Returns:
        Class name in PascalCase format.

    Example:
        >>> build_class_name("nexus", "provider")
        "NexusProvider"
        >>> build_class_name("github", "versioner")
        "GithubVersioner"
        >>> build_class_name("key_pair", "auth.pygit_authentication")
        "KeyPairPygitAuthentication"

    """
    module_name = build_module_name(name, package)
    return snake_to_pascal(module_name)
