"""Factory functions for PyGit authentication classes.

This module provides factory functions for creating PyGit authentication instances
using dynamic class instantiation based on string names.
"""

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)
from kbot_installer.core.factory.factory import factory_method


def create_pygit_authentication(name: str, **kwargs: object) -> PyGitAuthenticationBase:
    """Create a PyGit authentication instance by name.

    This function dynamically creates an instance of a PyGit authentication class
    based on the provided name. It follows the naming convention where:
    - Module name: {name}_pygit_authentication
    - Class name: {Name}PygitAuthentication (PascalCase)

    Args:
        name (str): Base name of the authentication type (e.g., "key_pair", "user_pass").
        **kwargs (object): Keyword arguments to pass to the authentication class constructor.

    Returns:
        PyGitAuthenticationBase: An instance of the specified authentication class.

    Raises:
        ImportError: If the authentication module cannot be imported.
        AttributeError: If the authentication class is not found in the module.
        TypeError: If the authentication class cannot be instantiated with the provided arguments.

    Example:
        >>> # Create key pair authentication
        >>> auth = create_pygit_authentication(
        ...     "key_pair",
        ...     username="git",
        ...     private_key_path="/path/to/private_key",
        ...     public_key_path="/path/to/public_key",
        ...     passphrase=""
        ... )
        >>> print(type(auth))
        <class 'auth.pygit_authentication.key_pair_pygit_authentication.KeyPairPygitAuthentication'>

        >>> # Create user/password authentication
        >>> auth = create_pygit_authentication(
        ...     "user_pass",
        ...     username="user",
        ...     password="password"
        ... )
        >>> print(type(auth))
        <class 'auth.pygit_authentication.user_pass_pygit_authentication.UserPassPygitAuthentication'>

    """
    return factory_method(name, __package__, **kwargs)
