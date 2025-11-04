"""Dynamic API client for HTTP requests without schema constraints."""

from contextlib import asynccontextmanager
from typing import Any

import httpx

from .exceptions import HttpClientError, RequestTimeoutError
from .types import Auth, AuthType
from .utils.response_handler import ResponseHandler
from .utils.url_builder import URLBuilder


class ApiClient:
    """Dynamic API client that allows building paths dynamically.

    This client provides a fluent interface for constructing API paths
    and making HTTP requests without predefined schema constraints.

    Example:
        client = ApiClient("https://api.example.com", auth=BasicAuth("user", "pass"))
        response = await client.api.v1.repo(id=123).files(file_id=456).get()

    """

    def __init__(
        self,
        base_url: str,
        auth: AuthType = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for the API
            auth: Authentication method (BasicAuth, BearerAuth, etc.)
            timeout: Request timeout in seconds
            headers: Default headers to include with all requests

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_headers = headers or {}
        self._url_builder = URLBuilder(base_url)
        self._response_handler = ResponseHandler()

        # Prepare auth for httpx
        self._auth = self._prepare_auth(auth)

    def _prepare_auth(self, auth: AuthType) -> httpx.Auth | None:
        """Prepare authentication for httpx.

        Args:
            auth: Authentication object

        Returns:
            httpx.Auth object or None

        """
        if auth is None:
            return None

        if isinstance(auth, Auth):
            return auth.get_auth()

        if isinstance(auth, httpx.Auth):
            return auth

        msg = f"Unsupported auth type: {type(auth)}"
        raise ValueError(msg)

    def __getattr__(self, name: str) -> "ApiPath":
        """Enable dynamic path construction.

        Args:
            name: Path segment name

        Returns:
            ApiPath object for further chaining

        """
        return ApiPath(self, [name])

    async def execute(
        self,
        method: str,
        path: str,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> httpx.Response:
        """Execute an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: API path
            path_params: Parameters to substitute in path
            query_params: Query parameters
            headers: Additional headers
            json_data: JSON data for request body
            data: Form data for request body
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response object

        Raises:
            HttpClientError: If request fails
            TimeoutError: If request times out

        """
        # Substitute path parameters
        if path_params:
            path = self._url_builder.substitute_path_params(path, path_params)

        # Build complete URL
        url = self._url_builder.build_url(path, query_params)

        # Merge headers
        request_headers = {**self.default_headers, **(headers or {})}

        # Prepare request data
        request_data = {}
        if json_data is not None:
            request_data["json"] = json_data
        if data is not None:
            request_data["data"] = data

        try:
            async with httpx.AsyncClient(
                auth=self._auth, timeout=self.timeout, **kwargs
            ) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=request_headers,
                    **request_data,
                )

                return self._response_handler.handle_response(response)

        except httpx.TimeoutException as e:
            error_msg = f"Request timed out after {self.timeout}s"
            raise RequestTimeoutError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Request failed: {e}"
            raise HttpClientError(error_msg) from e

    @asynccontextmanager
    async def session(self) -> "ApiClient":
        """Context manager for persistent session.

        Yields:
            ApiClient with persistent httpx session

        """
        async with httpx.AsyncClient(
            auth=self._auth, timeout=self.timeout, headers=self.default_headers
        ) as client:
            # Create a new instance with the persistent client
            session_client = ApiClient(
                self.base_url,
                auth=self._auth,
                timeout=self.timeout,
                headers=self.default_headers,
            )
            session_client._client = client
            yield session_client


class ApiPath:
    """Represents a path segment in the API URL construction.

    This class enables fluent path construction and parameter substitution.
    """

    def __init__(self, client: ApiClient, path_segments: list[str]) -> None:
        """Initialize API path.

        Args:
            client: Reference to the API client
            path_segments: List of path segments built so far

        """
        self.client = client
        self.path_segments = path_segments
        self.path_params: dict[str, Any] = {}
        self.query_params: dict[str, Any] | None = None

    def __getattr__(self, name: str) -> "ApiPath":
        """Add another path segment.

        Args:
            name: Path segment name

        Returns:
            New ApiPath with additional segment

        """
        new_segments = [*self.path_segments, name]
        new_path = ApiPath(self.client, new_segments)
        new_path.path_params = self.path_params.copy()
        new_path.query_params = self.query_params.copy() if self.query_params else None
        return new_path

    def __call__(self, **path_params: object) -> "ApiPath":
        """Add path parameters.

        Args:
            **path_params: Parameters to substitute in path

        Returns:
            New ApiPath with parameters

        """
        new_path = ApiPath(self.client, self.path_segments)
        new_path.path_params = {**self.path_params, **path_params}
        new_path.query_params = self.query_params.copy() if self.query_params else None
        return new_path

    def query(self, **query_params: object) -> "QueryPath":
        """Add query parameters.

        Args:
            **query_params: Query parameters

        Returns:
            QueryPath object for further chaining

        """
        return QueryPath(
            self.client, self.path_segments, self.path_params, query_params
        )

    def _build_path(self) -> str:
        """Build the complete path string.

        Returns:
            Complete path string

        """
        path = self.client._url_builder.build_path(self.path_segments)  # noqa: SLF001
        if self.path_params:
            path = self.client._url_builder.substitute_path_params(  # noqa: SLF001
                path, self.path_params
            )
        return path

    async def get(self, **kwargs: object) -> httpx.Response:
        """Execute GET request.

        Args:
            **kwargs: Additional arguments for the request

        Returns:
            HTTP response object

        """
        return await self.client.execute(
            method="GET",
            path=self._build_path(),
            query_params=self.query_params,
            **kwargs,
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
            method="POST",
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
            method="PUT",
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
            method="DELETE",
            path=self._build_path(),
            query_params=self.query_params,
            **kwargs,
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
            method="PATCH",
            path=self._build_path(),
            query_params=self.query_params,
            json_data=json_data,
            data=data,
            **kwargs,
        )


class QueryPath(ApiPath):
    """Represents a path with query parameters.

    This class extends ApiPath to handle query parameters.
    """

    def __init__(
        self,
        client: ApiClient,
        path_segments: list[str],
        path_params: dict[str, Any],
        query_params: dict[str, Any],
    ) -> None:
        """Initialize query path.

        Args:
            client: Reference to the API client
            path_segments: List of path segments
            path_params: Path parameters
            query_params: Query parameters

        """
        super().__init__(client, path_segments)
        self.path_params = path_params
        self.query_params = query_params

    def query(self, **additional_query_params: object) -> "QueryPath":
        """Add more query parameters.

        Args:
            **additional_query_params: Additional query parameters

        Returns:
            New QueryPath with merged parameters

        """
        merged_params = {**self.query_params, **additional_query_params}
        return QueryPath(
            self.client, self.path_segments, self.path_params, merged_params
        )
