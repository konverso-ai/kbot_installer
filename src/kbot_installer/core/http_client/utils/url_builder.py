"""URL building utilities for the HTTP client."""

from urllib.parse import urlencode, urljoin


class URLBuilder:
    """Utility class for building URLs with path and query parameters."""

    def __init__(self, base_url: str) -> None:
        """Initialize URL builder.

        Args:
            base_url: Base URL for the API

        """
        self.base_url = base_url.rstrip("/")

    def build_path(self, path_segments: list[str]) -> str:
        """Build a path from segments.

        Args:
            path_segments: List of path segments

        Returns:
            Built path string

        """
        if not path_segments:
            return ""

        # Filter out empty segments
        segments = [str(seg).strip("/") for seg in path_segments if seg]
        return "/" + "/".join(segments)

    def build_url(
        self, path: str, query_params: dict[str, object] | None = None
    ) -> str:
        """Build complete URL with path and query parameters.

        Args:
            path: API path
            query_params: Query parameters

        Returns:
            Complete URL string

        """
        # Ensure path starts with /
        if path and not path.startswith("/"):
            path = "/" + path

        url = urljoin(self.base_url + "/", path.lstrip("/"))

        if query_params:
            # Filter out None values
            filtered_params = {k: v for k, v in query_params.items() if v is not None}
            if filtered_params:
                url += "?" + urlencode(filtered_params)

        return url

    def substitute_path_params(self, path: str, path_params: dict[str, object]) -> str:
        """Substitute path parameters in the format {param}.

        Args:
            path: Path template with {param} placeholders
            path_params: Parameters to substitute

        Returns:
            Path with substituted parameters

        """
        result = path
        for key, value in path_params.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))

        return result
