"""Bearer HTTP authentication for HTTP operations.

This module provides authentication using bearer tokens for HTTP requests.
"""

import httpx

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase


class BearerHttpAuth(HttpAuthBase, httpx.Auth):
    """Authentication class using bearer tokens.

    This class provides bearer token authentication for HTTP requests.
    It implements both HttpAuthBase interface and httpx.Auth protocol.

    Attributes:
        token (str): Bearer token for authentication.

    """

    def __init__(self, token: str) -> None:
        """Initialize bearer HTTP authentication.

        Args:
            token (str): Bearer token for authentication.

        """
        self.token = token

    def get_auth(self) -> httpx.Auth:
        """Get bearer HTTP authentication object.

        Returns:
            httpx.Auth: Bearer authentication object for HTTP requests.

        """
        return self

    def auth_flow(self, request: httpx.Request) -> httpx.Request:
        """Add bearer token to the request headers.

        This method is required by the httpx.Auth protocol and adds the
        Authorization header with the bearer token to the request.

        Args:
            request (httpx.Request): The HTTP request to authenticate.

        Yields:
            httpx.Request: The authenticated HTTP request.

        """
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request
