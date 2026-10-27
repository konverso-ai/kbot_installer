"""KB11111 coded error (sample)."""

from errors.base import ErrorCode


class KB11111(ErrorCode):
    """The bot database is running out of threads."""

    level = "warning"
    code = "KB11111"
    message = "Database running out of threads"
