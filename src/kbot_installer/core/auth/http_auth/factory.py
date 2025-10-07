"""Factory functions for HTTP authentication classes.

This module provides factory functions for creating HTTP authentication instances
using dynamic class instantiation based on string names.
"""

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase
from kbot_installer.core.factory.factory import factory_method


def create_http_auth(name: str, **kwargs: object) -> HttpAuthBase:
    """Create an HTTP authentication instance by name.

    This function dynamically creates an instance of an HTTP authentication class
    based on the provided name. It follows the naming convention where:
    - Module name: {name}_http_auth
    - Class name: {Name}HttpAuth (PascalCase)

    Args:
        name (str): Base name of the authentication type (e.g., "basic", "bearer").
        **kwargs (object): Keyword arguments to pass to the authentication class constructor.

    Returns:
        HttpAuthBase: An instance of the specified authentication class.

    Raises:
        ImportError: If the authentication module cannot be imported.
        AttributeError: If the authentication class is not found in the module.
        TypeError: If the authentication class cannot be instantiated with the provided arguments.

    Example:
        >>> # Create basic authentication
        >>> auth = create_http_auth(
        ...     "basic",
        ...     username="user",
        ...     password="password"
        ... )
        >>> print(type(auth))
        <class 'auth.http_auth.basic_http_auth.BasicHttpAuth'>

        >>> # Create bearer authentication
        >>> auth = create_http_auth(
        ...     "bearer",
        ...     token="your_token_here"
        ... )
        >>> print(type(auth))
        <class 'auth.http_auth.bearer_http_auth.BearerHttpAuth'>

    """
    return factory_method(name, __package__, **kwargs)
