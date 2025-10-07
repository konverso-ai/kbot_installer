"""Response handling utilities for the HTTP client."""

import httpx

from http_client.exceptions import ResponseError


class ResponseHandler:
    """Utility class for handling HTTP responses."""

    @staticmethod
    def handle_response(response: httpx.Response) -> httpx.Response:
        """Handle HTTP response and raise appropriate errors.

        Args:
            response: HTTP response object

        Returns:
            The response object

        Raises:
            ResponseError: If response indicates an error

        """
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise ResponseError(error_msg) from e

        return response

    @staticmethod
    def get_json(response: httpx.Response) -> dict[str, object]:
        """Extract JSON data from response.

        Args:
            response: HTTP response object

        Returns:
            JSON data as dictionary

        Raises:
            ResponseError: If JSON parsing fails

        """
        try:
            return response.json()
        except Exception as e:
            error_msg = f"Failed to parse JSON response: {e}"
            raise ResponseError(error_msg) from e

    @staticmethod
    def get_text(response: httpx.Response) -> str:
        """Extract text data from response.

        Args:
            response: HTTP response object

        Returns:
            Text content

        """
        return response.text

    @staticmethod
    def get_headers(response: httpx.Response) -> dict[str, str]:
        """Extract headers from response.

        Args:
            response: HTTP response object

        Returns:
            Headers as dictionary

        """
        return dict(response.headers)
