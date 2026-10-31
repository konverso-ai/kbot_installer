"""Tests for utils.bundle module."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from utils.bundle import Bundle
from utils.product.product import Product
from utils.version import Version


class TestConstruction:
    """Test cases for basic field construction and validation."""

    def test_minimal_bundle_uses_defaults(self) -> None:
        """Test that a bundle built with only name/version/versions gets defaults."""
        bundle = Bundle(name="demo", version="1.2.3", versions=[])

        assert bundle.name == "demo"
        assert bundle.version == Version("1.2.3")
        assert bundle.created_by == ""
        assert bundle.created_on == ""
        assert bundle.created_from == ""
        assert bundle.timestamp == ""
        assert bundle.versions == []

    def test_version_validator_accepts_version_instance(self) -> None:
        """Test that an existing Version instance is preserved."""
        version = Version("1.2.3")
        bundle = Bundle(name="demo", version=version, versions=[])

        assert bundle.version == version

    def test_version_validator_rejects_empty_version(self) -> None:
        """Test that an empty version raises ValueError."""
        with pytest.raises(ValueError, match="Bundle version is required"):
            Bundle(name="demo", version="", versions=[])

    def test_version_validator_rejects_none_version(self) -> None:
        """Test that a None version raises ValueError."""
        with pytest.raises(ValueError, match="Bundle version is required"):
            Bundle(name="demo", version=None, versions=[])

    def test_versions_field_holds_products(self) -> None:
        """Test that versions accepts a list of Product instances."""
        product = Product(name="p1", version="1.0.0")
        bundle = Bundle(name="demo", version="1.0.0", versions=[product])

        assert bundle.versions == [product]

    def test_model_dump_serializes_version_via_field_serializer(self) -> None:
        """Test that model_dump uses the version field_serializer (to_str)."""
        bundle = Bundle(name="demo", version="1.2.3", versions=[])

        dumped = bundle.model_dump()

        assert dumped["version"] == Version("1.2.3").to_str()


class TestFileName:
    """Test cases for Bundle.file_name."""

    def test_file_name_without_version(self) -> None:
        """Test that file_name without a version returns '{name}.json'."""
        assert Bundle.file_name("demo") == Path("demo.json")

    def test_file_name_with_version(self) -> None:
        """Test that file_name with a version returns '{name}-{version}.json'."""
        result = Bundle.file_name("demo", Version("1.2.3"))

        assert result == Path(f"demo-{Version('1.2.3')}.json")


class TestFromName:
    """Test cases for Bundle.from_name."""

    def test_from_name_splits_name_and_version_but_requires_versions_field(
        self,
    ) -> None:
        """Test from_name parses name/version but requires versions field.

        The ``versions`` field is required but omitted by ``from_name``,
        causing pydantic validation to fail.
        """
        with pytest.raises(ValidationError, match="versions"):
            Bundle.from_name("demo-1.2.3")

    def test_from_name_raises_value_error_without_separator(self) -> None:
        """Test that a name without a '-' separator raises ValueError."""
        with pytest.raises(ValueError, match="not enough values to unpack"):
            Bundle.from_name("demo")


class TestFromJson:
    """Test cases for Bundle.from_json."""

    def test_from_json_parses_json_string(self) -> None:
        """Test that a JSON string is parsed into a Bundle."""
        payload = json.dumps(
            {"name": "demo", "version": "1.2.3", "versions": []}
        )

        bundle = Bundle.from_json(payload)

        assert bundle.name == "demo"
        assert bundle.version == Version("1.2.3")
        assert bundle.versions == []

    def test_from_json_accepts_already_parsed_dict(self) -> None:
        """Test that a pre-parsed dict is accepted directly."""
        bundle = Bundle.from_json(
            {"name": "demo", "version": "1.2.3", "versions": []}
        )

        assert bundle.name == "demo"

    def test_from_json_parses_nested_product_versions(self) -> None:
        """Test that nested product dicts in versions are parsed into Products."""
        payload = {
            "name": "demo",
            "version": "1.2.3",
            "versions": [{"name": "p1", "version": "1.0.0"}],
        }

        bundle = Bundle.from_json(payload)

        assert len(bundle.versions) == 1
        assert isinstance(bundle.versions[0], Product)
        assert bundle.versions[0].name == "p1"

    def test_from_json_invalid_json_string_raises(self) -> None:
        """Test that invalid JSON text raises a JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            Bundle.from_json("not-json")


class TestToJson:
    """Test cases for Bundle.to_json."""

    def test_to_json_returns_expected_shape(self) -> None:
        """Test that to_json produces a dict with all expected keys."""
        bundle = Bundle(
            name="demo",
            version="1.2.3",
            created_by="alice",
            created_on="2024-01-01",
            created_from="ci",
            timestamp="2024-01-01T00:00:00",
            versions=[],
        )

        data = bundle.to_json()

        assert data == {
            "name": "demo",
            "version": bundle.version.to_json_str(),
            "created_by": "alice",
            "created_on": "2024-01-01",
            "created_from": "ci",
            "timestamp": "2024-01-01T00:00:00",
            "versions": [],
        }

    def test_to_json_serializes_nested_products(self) -> None:
        """Test that versions are serialized via Product.to_json."""
        product = Product(name="p1", version="1.0.0")
        bundle = Bundle(name="demo", version="1.2.3", versions=[product])

        data = bundle.to_json()

        assert data["versions"] == [product.to_json()]

    def test_to_json_round_trips_through_from_json(self) -> None:
        """Test that to_json output can be re-parsed by from_json."""
        product = Product(name="p1", version="1.0.0")
        bundle = Bundle(name="demo", version="1.2.3", versions=[product])

        round_tripped = Bundle.from_json(bundle.to_json())

        assert round_tripped.name == bundle.name
        assert round_tripped.version == bundle.version
        assert round_tripped.versions[0].name == "p1"


class TestExport:
    """Test cases for Bundle.export."""

    def test_export_json_writes_file_with_default_name(self, tmp_path, monkeypatch) -> None:
        """Test that export('json') writes to the default file name when no path given."""
        monkeypatch.chdir(tmp_path)
        bundle = Bundle(name="demo", version="1.2.3", versions=[])

        bundle.export("json")

        destination = tmp_path / Bundle.file_name("demo", Version("1.2.3"))
        assert destination.exists()
        assert json.loads(destination.read_text(encoding="utf-8")) == bundle.to_json()

    def test_export_json_writes_file_at_given_path(self, tmp_path: Path) -> None:
        """Test that export('json', path) writes JSON content to the given path."""
        bundle = Bundle(name="demo", version="1.2.3", versions=[])
        destination = tmp_path / "custom.json"

        bundle.export("json", destination)

        assert json.loads(destination.read_text(encoding="utf-8")) == bundle.to_json()

    def test_export_unsupported_mode_raises_attribute_error(
        self, tmp_path: Path
    ) -> None:
        """Test that an unsupported mode raises AttributeError."""
        bundle = Bundle(name="demo", version="1.2.3", versions=[])

        with pytest.raises(AttributeError):
            bundle.export("yaml", tmp_path / "bundle.yaml")  # type: ignore[arg-type]
