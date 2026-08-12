"""Tests for errors package."""

import pytest

from errors import ErrorCode, KB11111, LLM00001
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "error_cls, params, expected_message, expected_level",
    [
        (
            KB11111,
            {},
            "KB11111: Database running out of threads",
            "warning",
        ),
        (
            KB11111,
            {"message": "Custom thread warning"},
            "KB11111: Custom thread warning",
            "warning",
        ),
        (
            KB11111,
            {"level": "error"},
            "KB11111: Database running out of threads",
            "error",
        ),
        (
            LLM00001,
            {},
            "LLM00001: Prompt blocked by a guardrail",
            "debug",
        ),
    ],
)
def test_errorcode_valid_formats_message(
    error_cls: type[ErrorCode],
    params: dict,
    expected_message: str,
    expected_level: str,
) -> None:
    error = error_cls(**params)
    assert compare("eq", str(error), expected_message)
    assert compare("eq", repr(error), expected_message)
    assert compare("eq", error.level, expected_level)
