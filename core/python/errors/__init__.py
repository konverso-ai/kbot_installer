from typing import Literal

from typing_extensions import override


class ErrorCode(BaseException):

    code: str = ''

    # Default message, which may be overriden at runtime
    message: str = ''

    level: Literal["critical", "error", "warning"] = "warning"

    def __init__(
        self,
        *,
        message: str | None = None,
        level: Literal["critical", "error", "warning"] | None = None,
    ):
        """Create a new error, using the level and message defined in the class
           or in the overidden constructor parameters.
        """

        if message:
            self.message = message

        if level:
            self.level = level

        super().__init__(self, f"{self.code}: {self.message}")

    @override
    def __str__(self) -> str:
        return f'{self.code}: {self.message}'

    @override
    def __repr__(self) -> str:
        return str(self)

# A sample error
class KB11111(ErrorCode):
    """
    Indicates the bot database is running out of thread
    """
    level = "warning"
    code = "KB11111"
    message = "Database running out of threads"


class LLM00001(ErrorCode):
    """
    Indicates that the prompt was blocked by a guardrail
    """
    level = "debug"
    code = "LLM00001"
    message = "Prompt blocked by a guardrail"
