"""Tests for publisher.factory module."""

from unittest.mock import MagicMock

from publisher.bundle_publisher import BundlePublisher
from publisher.factory import create_publisher
from utils.utils_for_unit_tests import compare


def test_createpublisher_valid_returns_bundle_publisher() -> None:
    storage = MagicMock()
    publisher = create_publisher("bundle", storage=storage)
    assert compare("eq", isinstance(publisher, BundlePublisher), True)
