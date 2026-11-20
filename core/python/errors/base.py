"""Base class of the coded errors.

``errors`` is a namespace package shared by kbot_installer and the products (kbot ships
``errors/factory.py`` and its own codes): never add an ``errors/__init__.py``. Each concrete error
lives in its own module named after its code in lowercase (``errors/kb0002.py`` defines ``KB0002``).
"""

from typing import Literal, TypeAlias

from typing_extensions import override

ErrorLevel: TypeAlias = Literal["critical", "error", "warning", "info", "debug"]


class ErrorCode(BaseException):
    """Error identified by a stable code, with a default message and log level.

    It extends ``BaseException``, so ``except Exception`` does not catch it.
    """

    code: str = ""

    # Default message, which may be overridden at runtime
    message: str = ""
    documentation_link: str = ""

    level: ErrorLevel = "warning"

    def __init__(
        self,
        *,
        message: str | None = None,
        level: ErrorLevel | None = None,
    ) -> None:
        """Create a new error, using the level and message of the class unless overridden here."""
        if message:
            self.message = message

        if level:
            self.level = level

        super().__init__(self, f"{self.code}: {self.message}")

    @override
    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    @override
    def __repr__(self) -> str:
        return str(self)
