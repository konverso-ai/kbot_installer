"""Tests for publisher package exports."""

from publisher import PublisherBase, create_publisher
from utils.utils_for_unit_tests import compare


def test_init_valid_exports_public_api() -> None:
    assert compare("eq", callable(create_publisher), True)
    assert compare("eq", PublisherBase.__name__, "PublisherBase")
