"""Tests for publisher.bundle_publisher module."""

from unittest.mock import MagicMock

from publisher.bundle_publisher import BundlePublisher
from utils.bundle import Bundle
from utils.product import Product
from utils.utils_for_unit_tests import compare
from utils.version import Version


def test_publish_valid_writes_bundle_json_to_storage() -> None:
    storage = MagicMock()
    publisher = BundlePublisher(storage=storage)
    bundle = Bundle(
        name="core",
        version=Version.parse("2025.01"),
        created_by="tester",
        created_on="2025-01-01",
        created_from="local",
        timestamp="2025-01-01T00:00:00",
        versions=[Product.from_dict({"name": "jira", "version": "2025.01"})],
    )

    publisher.publish(bundle)

    storage.set.assert_called_once()
    key, content = storage.set.call_args.args
    assert compare("eq", key, "core-2025.1.0000.json")
    assert compare("in", '"name":"core"', content)
