"""Enhanced HTTP client using furl for robust URL management."""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from kbot_installer.core.url_manager.url_manager_base import URLManagerBase

from kbot_installer.core.url_manager import create_url_manager

from .exceptions import HttpClientError, RequestTimeoutError
from .types import Auth, AuthType
from .utils.response_handler import ResponseHandler


class EnhancedApiClient:
    """Enhanced HTTP client with robust URL management using furl.

    This client provides the same dynamic API interaction capabilities as ApiClient
    but with enhanced URL management using the furl library for more robust
    URL parsing, construction, and manipulation.

    Example:
        >>> import asyncio
        >>> from http_client import EnhancedApiClient, BasicAuth
        >>>
        >>> async def main():
        >>>     client = EnhancedApiClient(
        ...         "https://api.example.com", auth=BasicAuth("user", "pass")
        ...     )
        >>>     response = await client.api.v1.repo(id=123).files(file_id=456).get()
        >>>     print(response.json())
        >>>
        >>> if __name__ == "__main__":
        >>>     asyncio.run(main())

    """

    def __init__(
        self,
        base_url: str,
        auth: AuthType = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the enhanced API client.

        Args:
            base_url: Base URL for the API
            auth: Authentication method (BasicAuth, BearerAuth, etc.)
            timeout: Request timeout in seconds
            headers: Default headers to send with each request

        """
        self.base_url = base_url
        self.timeout = timeout
        self.default_headers = headers if headers is not None else {}
        self._auth = self._prepare_auth(auth)
        self._url_manager = create_url_manager("furl", base_url)
        self._response_handler = ResponseHandler()
        self._session = httpx.AsyncClient(
            auth=self._auth, timeout=self.timeout, headers=self.default_headers
        )

    def _prepare_auth(self, auth: AuthType) -> httpx.Auth | None:
        """Prepare the httpx.Auth object from the provided AuthType."""
        if isinstance(auth, Auth):
            return auth.get_auth()
        return auth

    def __getattr__(self, name: str) -> "EnhancedApiPath":
        """Allow dynamic path segment construction (e.g., client.api.v1)."""
        return EnhancedApiPath(self, [name])

    @asynccontextmanager
    async def session(self) -> "EnhancedApiClient":
        """Context manager for persistent session.

        Yields:
            EnhancedApiClient: The client instance for use within the context.

        """
        async with self._session as session:
            self._session = session
            yield self

    async def execute(
        self,
        method: str,
        path: str,
        query_params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> httpx.Response:
        """Execute an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            path: API path (e.g., "/api/v1/users")
            query_params: Dictionary of query parameters
            path_params: Dictionary of path parameters
            json_data: JSON data for the request body
            data: Form data for the request body
            **kwargs: Additional arguments for the httpx.request method

        Returns:
            httpx.Response: The HTTP response object

        Raises:
            RequestTimeoutError: If the request times out
            HttpClientError: For other request-related errors
            ResponseError: If the response indicates an HTTP error

        """
        # Build URL using URL manager
        url_manager = self._url_manager.from_string(self.base_url + path)

        # Add path parameters by substituting placeholders
        if path_params:
            url_str = str(url_manager)
            for key, value in path_params.items():
                url_str = url_str.replace(f"{{{key}}}", str(value))
            url_manager = url_manager.from_string(url_str)

        # Add query parameters
        if query_params:
            url_manager = url_manager.add_params(**query_params)

        url = str(url_manager)
        try:
            response = await self._session.request(
                method, url, json=json_data, data=data, **kwargs
            )

            return self._response_handler.handle_response(response)

        except httpx.TimeoutException as e:
            error_msg = f"Request timed out after {self.timeout}s"
            raise RequestTimeoutError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Request failed: {e}"
            raise HttpClientError(error_msg) from e

    def get_url_manager(self) -> "URLManagerBase":
        """Get the URL manager instance for advanced URL operations.

        Returns:
            URLManagerBase: The URL manager instance

        """
        return self._url_manager


class EnhancedApiPath:
    """Enhanced API path with robust URL management using furl."""

    def __init__(
        self,
        client: EnhancedApiClient,
        path_segments: list[str] | None = None,
        path_params: dict[str, Any] | None = None,
    ) -> None:
        """Initialize enhanced API path.

        Args:
            client: Reference to the enhanced API client
            path_segments: List of accumulated path segments
            path_params: Dictionary of path parameters

        """
        self.client = client
        self.path_segments = path_segments if path_segments is not None else []
        self.path_params = path_params if path_params is not None else {}
        self.query_params: dict[str, Any] = {}

    def __getattr__(self, name: str) -> "EnhancedApiPath":
        """Append a new dynamic path segment (e.g., .v1.repo)."""
        new_segments = [*self.path_segments, name]
        return EnhancedApiPath(self.client, new_segments, self.path_params)

    def __call__(self, **path_params: object) -> "EnhancedApiPath":
        """Add dynamic path parameters (e.g., .repo(id=3))."""
        new_path_params = {**self.path_params, **path_params}
        return EnhancedApiPath(self.client, self.path_segments, new_path_params)

    def query(self, **additional_query_params: object) -> "EnhancedQueryPath":
        """Add query parameters to the path.

        Args:
            **additional_query_params: Additional query parameters

        Returns:
            A new EnhancedQueryPath instance with merged query parameters.

        """
        new_query_params = {**self.query_params, **additional_query_params}
        return EnhancedQueryPath(
            self.client, self.path_segments, self.path_params, new_query_params
        )

    def _build_path(self) -> str:
        """Build the complete path string.

        Returns:
            Complete path string

        """
        # Build path from segments
        path = "/" + "/".join(str(seg) for seg in self.path_segments if seg)

        # Substitute path parameters
        if self.path_params:
            for key, value in self.path_params.items():
                path = path.replace(f"{{{key}}}", str(value))

        return path

    async def get(self, **kwargs: object) -> httpx.Response:
        """Execute GET request.

        Args:
            **kwargs: Additional arguments for the request

        Returns:
            HTTP response object

        """
        return await self.client.execute(
            "GET", path=self._build_path(), query_params=self.query_params, **kwargs
        )

    async def post(
        self,
        json_data: dict[str, object] | None = None,
        data: dict[str, object] | None = None,
        **kwargs: object,
    ) -> httpx.Response:
        """Execute POST request.

        Args:
            json_data: JSON data for request body
            data: Form data for request body
            **kwargs: Additional arguments for the request

        Returns:
            HTTP response object

        """
        return await self.client.execute(
            "POST",
            path=self._build_path(),
            query_params=self.query_params,
            json_data=json_data,
            data=data,
            **kwargs,
        )

    async def put(
        self,
        json_data: dict[str, object] | None = None,
        data: dict[str, object] | None = None,
        **kwargs: object,
    ) -> httpx.Response:
        """Execute PUT request.

        Args:
            json_data: JSON data for request body
            data: Form data for request body
            **kwargs: Additional arguments for the request

        Returns:
            HTTP response object

        """
        return await self.client.execute(
            "PUT",
            path=self._build_path(),
            query_params=self.query_params,
            json_data=json_data,
            data=data,
            **kwargs,
        )

    async def delete(self, **kwargs: object) -> httpx.Response:
        """Execute DELETE request.

        Args:
            **kwargs: Additional arguments for the request

        Returns:
            HTTP response object

        """
        return await self.client.execute(
            "DELETE", path=self._build_path(), query_params=self.query_params, **kwargs
        )

    async def patch(
        self,
        json_data: dict[str, object] | None = None,
        data: dict[str, object] | None = None,
        **kwargs: object,
    ) -> httpx.Response:
        """Execute PATCH request.

        Args:
            json_data: JSON data for request body
            data: Form data for request body
            **kwargs: Additional arguments for the request

        Returns:
            HTTP response object

        """
        return await self.client.execute(
            "PATCH",
            path=self._build_path(),
            query_params=self.query_params,
            json_data=json_data,
            data=data,
            **kwargs,
        )


class EnhancedQueryPath(EnhancedApiPath):
    """Enhanced query path with robust URL management using furl.

    This class extends EnhancedApiPath to handle query parameters with
    enhanced URL management capabilities.
    """

    def __init__(
        self,
        client: EnhancedApiClient,
        path_segments: list[str],
        path_params: dict[str, Any],
        query_params: dict[str, Any],
    ) -> None:
        """Initialize enhanced query path.

        Args:
            client: Reference to the enhanced API client
            path_segments: List of path segments
            path_params: Dictionary of path parameters
            query_params: Dictionary of query parameters

        """
        super().__init__(client, path_segments)
        self.path_params = path_params
        self.query_params = query_params

    def query(self, **additional_query_params: object) -> "EnhancedQueryPath":
        """Add more query parameters.

        Args:
            **additional_query_params: Additional query parameters

        Returns:
            New EnhancedQueryPath with merged parameters

        """
        new_query_params = {**self.query_params, **additional_query_params}
        return EnhancedQueryPath(
            self.client, self.path_segments, self.path_params, new_query_params
        )

    def add_query_param(
        self, key: str, *, value: str | float | bool | None
    ) -> "EnhancedQueryPath":
        """Add a single query parameter.

        Args:
            key: Parameter key
            value: Parameter value

        Returns:
            New EnhancedQueryPath with added parameter

        """
        new_query_params = {**self.query_params, key: value}
        return EnhancedQueryPath(
            self.client, self.path_segments, self.path_params, new_query_params
        )

    def remove_query_param(self, key: str) -> "EnhancedQueryPath":
        """Remove a query parameter.

        Args:
            key: Parameter key to remove

        Returns:
            New EnhancedQueryPath without the parameter

        """
        new_query_params = {k: v for k, v in self.query_params.items() if k != key}
        return EnhancedQueryPath(
            self.client, self.path_segments, self.path_params, new_query_params
        )

    def clear_query_params(self) -> "EnhancedQueryPath":
        """Clear all query parameters.

        Returns:
            New EnhancedQueryPath without query parameters

        """
        return EnhancedQueryPath(self.client, self.path_segments, self.path_params, {})

    def get_full_url(self) -> str:
        """Get the full URL with all parameters.

        Returns:
            Complete URL string

        """
        path = self._build_path()
        # Build URL using the URL manager
        url_manager = self.client.get_url_manager().from_string(
            self.client.base_url + path
        )

        # Add query parameters
        if self.query_params:
            url_manager = url_manager.add_params(**self.query_params)

        return str(url_manager)
