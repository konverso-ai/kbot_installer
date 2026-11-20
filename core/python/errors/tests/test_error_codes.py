"""Tests for the coded errors of the errors namespace package."""

import pytest

from errors.base import ErrorCode
from errors.kb0002 import KB0002
from errors.kb11111 import KB11111
from errors.llm00001 import LLM00001
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    ("error_cls", "params", "expected_message", "expected_level"),
    [
        (KB11111, {}, "KB11111: Database running out of threads", "warning"),
        (KB11111, {"message": "Custom thread warning"}, "KB11111: Custom thread warning", "warning"),
        (KB11111, {"level": "error"}, "KB11111: Database running out of threads", "error"),
        (LLM00001, {}, "LLM00001: Prompt blocked by a guardrail", "debug"),
        (KB0002, {}, "KB0002: Call to Konverso File Manager failed", "warning"),
    ],
)
def test_errorcode_formats_code_and_message(
    error_cls: type[ErrorCode],
    params: dict,
    expected_message: str,
    expected_level: str,
) -> None:
    error = error_cls(**params)

    assert compare("eq", str(error), expected_message)
    assert compare("eq", repr(error), expected_message)
    assert compare("eq", error.level, expected_level)


def test_errorcode_override_does_not_leak_to_class_default() -> None:
    KB11111(message="Custom thread warning", level="error")

    assert compare("eq", str(KB11111()), "KB11111: Database running out of threads")
    assert compare("eq", KB11111().level, "warning")


def test_errorcode_is_not_caught_by_except_exception() -> None:
    with pytest.raises(LLM00001):
        try:
            raise LLM00001
        except Exception:  # noqa: BLE001 - asserting coded errors bypass generic handlers
            pytest.fail("ErrorCode must extend BaseException, not Exception")
