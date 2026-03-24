"""Basic HTTP authentication for HTTP operations.

This module provides authentication using username and password for HTTP requests.
"""

import httpx

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase


class BasicHttpAuth(HttpAuthBase):
    """Authentication class using username and password.

    This class provides basic HTTP authentication for HTTP requests using
    username and password. It implements the HttpAuthBase interface.

    Attributes:
        username (str): Username for authentication.
        password (str): Password for authentication.

    """

    def __init__(self, username: str, password: str) -> None:
        """Initialize basic HTTP authentication.

        Args:
            username (str): Username for authentication.
            password (str): Password for authentication.

        """
        self.username = username
        self.password = password

    def get_auth(self) -> httpx.Auth:
        """Get basic HTTP authentication object.

        Returns:
            httpx.Auth: Basic authentication object for HTTP requests.

        """
        return httpx.BasicAuth(self.username, self.password)
