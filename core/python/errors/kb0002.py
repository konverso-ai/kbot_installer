"""KB0002 coded error."""

from errors.base import ErrorCode


class KB0002(ErrorCode):
    """A call to the Konverso File Manager failed."""

    level = "warning"
    code = "KB0002"
    message = "Call to Konverso File Manager failed"
