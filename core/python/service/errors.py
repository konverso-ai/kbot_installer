"""Service errors."""

from typing_extensions import override


class NexusHttpError(Exception):
    """HTTP error raised by Nexus API calls."""

    def __init__(self, status_code: int, message: str = "") -> None:
        """Initialize the error with the HTTP status code and message.

        Args:
            status_code: HTTP status code returned by the Nexus API.
            message: Optional error detail returned alongside the status code.

        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"HttpError({status_code}, {message})")

    @override
    def __str__(self) -> str:
        return f"HttpError({self.status_code}, {self.message})"
