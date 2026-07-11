from typing_extensions import override

"""Service errors."""


class NexusHttpError(Exception):
    """HTTP error raised by Nexus API calls."""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HttpError({status_code}, {message})")

    @override
    def __str__(self) -> str:
        return f"HttpError({self.status_code}, {self.message})"
