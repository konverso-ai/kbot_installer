"""Tests for utils.work_in_progress module."""

import pytest
from pydantic import ValidationError

from utils.work_in_progress import Setting, Settings
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "params, expected_value",
    [
        ({"name": "port", "type": "int", "default": 8080}, 8080),
        ({"name": "host", "type": "str", "value": "localhost"}, "localhost"),
    ],
)
def test_setting_valid_accepts_typed_values(
    params: dict,
    expected_value: int | str,
) -> None:
    setting = Setting(**params)
    assert compare("eq", setting.value, expected_value)
    assert compare("eq", setting.type.__name__, type(expected_value).__name__)


def test_settings_valid_indexes_by_name() -> None:
    settings = Settings.model_validate(
        [
            {"name": "port", "type": "int", "default": 8080},
            {"name": "host", "type": "str", "value": "localhost"},
        ]
    )
    assert compare("eq", settings["port"].value, 8080)
    assert compare("eq", len(settings), 2)
    assert compare("eq", "host" in settings, True)


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"name": "port", "type": "int"}, ValidationError),
        ({"name": "port", "type": "invalid", "default": 1}, ValidationError),
        (
            {"name": "port", "type": "int", "default": 8080, "choices": ["bad"]},
            ValidationError,
        ),
    ],
)
def test_setting_invalid_rejects_bad_configuration(
    params: dict,
    expected: type[BaseException],
) -> None:
    with pytest.raises(expected):
        _ = Setting(**params)
