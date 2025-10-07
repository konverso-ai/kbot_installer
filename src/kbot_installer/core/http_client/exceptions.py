"""Custom exceptions for the HTTP client package."""


class HttpClientError(Exception):
    """Base exception for HTTP client errors."""


class AuthenticationError(HttpClientError):
    """Raised when authentication fails."""


class RequestTimeoutError(HttpClientError):
    """Raised when a request times out."""


class ValidationError(HttpClientError):
    """Raised when request parameters are invalid."""


class PathConstructionError(HttpClientError):
    """Raised when path construction fails."""


class ResponseError(HttpClientError):
    """Raised when response processing fails."""
