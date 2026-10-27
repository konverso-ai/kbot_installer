"""LLM00001 coded error."""

from errors.base import ErrorCode


class LLM00001(ErrorCode):
    """The prompt was blocked by a guardrail."""

    level = "debug"
    code = "LLM00001"
    message = "Prompt blocked by a guardrail"
