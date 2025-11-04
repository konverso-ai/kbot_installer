"""Type definitions and interfaces for the HTTP client package."""

from abc import ABC, abstractmethod
from typing import Any

import httpx


class Auth(ABC):
    """Base interface for authentication methods."""

    @abstractmethod
    def get_auth(self) -> httpx.Auth:
        """Return the httpx.Auth object for authentication."""


class BasicAuth(Auth):
    """Basic authentication with username and password."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize Basic authentication.

        Args:
            username: Username for authentication
            password: Password for authentication

        """
        self.username = username
        self.password = password

    def get_auth(self) -> httpx.Auth:
        """Return httpx.BasicAuth object."""
        return httpx.BasicAuth(self.username, self.password)


class BearerAuth(Auth):
    """Bearer token authentication."""

    def __init__(self, token: str) -> None:
        """Initialize Bearer authentication.

        Args:
            token: Bearer token for authentication

        """
        self.token = token

    def get_auth(self) -> httpx.Auth:
        """Return custom auth that adds Bearer token to headers."""
        return httpx.Headers({"Authorization": f"Bearer {self.token}"})


class ApiKeyAuth(Auth):
    """API key authentication with configurable header or query parameter."""

    def __init__(
        self, api_key: str, header_name: str = "X-API-Key", *, in_query: bool = False
    ) -> None:
        """Initialize API key authentication.

        Args:
            api_key: API key value
            header_name: Name of the header to use (default: X-API-Key)
            in_query: Whether to put the key in query parameters instead of headers

        """
        self.api_key = api_key
        self.header_name = header_name
        self.in_query = in_query

    def get_auth(self) -> httpx.Auth:
        """Return custom auth that adds API key to headers or query."""
        if self.in_query:
            return httpx.QueryParams({self.header_name: self.api_key})
        return httpx.Headers({self.header_name: self.api_key})


# Type aliases for better readability
PathParams = dict[str, Any]
QueryParams = dict[str, Any]
Headers = dict[str, str]
AuthType = Auth | httpx.Auth | None
