"""Tests for snake_pascal module."""

import pytest

from utils.snake_pascal import pascal2snake, snake2pascal
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "name, expected",
    [
        ("NexusProvider", "nexus_provider"),
        ("HTTPResponse", "http_response"),
        ("word", "word"),
        ("", ""),
        ("GetHTTPResponseCode", "get_http_response_code"),
        ("my-api-key", "my_api_key"),
    ],
)
def test_pascal2snake_valid_converts_to_snake_case(name: str, expected: str) -> None:
    assert compare("eq", pascal2snake(name), expected)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("nexus_provider", "NexusProvider"),
        ("http_response", "HttpResponse"),
        ("word", "Word"),
        ("", ""),
        ("my_api_key", "MyApiKey"),
        ("___", ""),
        ("_leading", "Leading"),
        ("trailing_", "Trailing"),
        ("word__with___underscores", "WordWithUnderscores"),
    ],
)
def test_snake2pascal_valid_converts_to_pascal_case(name: str, expected: str) -> None:
    assert compare("eq", snake2pascal(name), expected)


@pytest.mark.parametrize(
    "name",
    [
        "nexus_provider",
        "http_response",
        "my_api_key",
        "word",
    ],
)
def test_snake2pascal_valid_roundtrip_with_pascal2snake(name: str) -> None:
    assert compare("eq", pascal2snake(snake2pascal(name)), name)


@pytest.mark.parametrize(
    "name",
    [
        "NexusProvider",
        "Word",
        "MyApiKey",
    ],
)
def test_pascal2snake_valid_roundtrip_with_snake2pascal(name: str) -> None:
    assert compare("eq", snake2pascal(pascal2snake(name)), name)
