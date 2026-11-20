"""Tests for utils.product.product module."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from utils.product.build import Build
from utils.product.categories import Categories
from utils.product.loc_display_mapper import LocDisplayMapper
from utils.product.loc_mapper import LocMapper
from utils.product.parents import Parents
from utils.product.product import Product
from utils.version import Version


class TestConstruction:
    """Test cases for basic field construction and defaults."""

    def test_minimal_product_uses_defaults(self) -> None:
        """Test that a product built with only a name gets sensible defaults."""
        product = Product(name="demo")

        assert product.name == "demo"
        assert product.version == Version.empty()
        assert product.doc is None
        assert product.build is None
        assert product.date == ""
        assert product.type == "solution"
        assert product.parents is None
        assert product.categories is None
        assert product.license is None
        assert product.display is None

    def test_name_is_required(self) -> None:
        """Test that omitting name raises a validation error."""
        with pytest.raises(ValidationError, match="name"):
            Product()  # type: ignore[call-arg]


class TestValidators:
    """Test cases for the field_validator conversions."""

    def test_version_validator_accepts_string(self) -> None:
        """Test that a version string is parsed into a Version instance."""
        product = Product(name="demo", version="1.2.3")

        assert product.version == Version("1.2.3")

    def test_version_validator_accepts_version_instance(self) -> None:
        """Test that an existing Version instance is preserved."""
        version = Version("1.2.3")
        product = Product(name="demo", version=version)

        assert product.version is version

    def test_version_validator_accepts_none(self) -> None:
        """Test that None produces an empty version."""
        product = Product(name="demo", version=None)

        assert product.version == Version.empty()

    def test_build_validator_accepts_string_timestamp(self) -> None:
        """Test that a plain string build value is converted to a Build."""
        product = Product(name="demo", build="2024-01-01T00:00:00")

        assert product.build == Build(
            timestamp="2024-01-01T00:00:00", branch="", commit=""
        )

    def test_build_validator_accepts_dict(self) -> None:
        """Test that a build dict is passed through untouched."""
        product = Product(
            name="demo",
            build={"timestamp": "ts", "branch": "main", "commit": "abc"},
        )

        assert product.build == Build(timestamp="ts", branch="main", commit="abc")

    def test_parents_validator_accepts_list_of_names(self) -> None:
        """Test that a plain list of names builds a Parents container."""
        product = Product(name="demo", parents=["p1", "p2"])

        assert product.parent_names == ["p1", "p2"]

    def test_parents_validator_accepts_structured_dict(self) -> None:
        """Test that an already-structured parents dict passes through."""
        product = Product(name="demo", parents={"parent": [{"@name": "p1"}]})

        assert product.parent_names == ["p1"]

    def test_categories_validator_accepts_list_of_names(self) -> None:
        """Test that a plain list of names builds a Categories container."""
        product = Product(name="demo", categories=["c1", "c2"])

        assert product.category_names == ["c1", "c2"]

    def test_categories_validator_accepts_structured_dict(self) -> None:
        """Test that an already-structured categories dict passes through."""
        product = Product(name="demo", categories={"category": [{"@name": "c1"}]})

        assert product.category_names == ["c1"]


class TestProperties:
    """Test cases for computed properties."""

    def test_parent_names_empty_when_no_parents(self) -> None:
        """Test that parent_names is empty when parents is None."""
        assert Product(name="demo").parent_names == []

    def test_parent_names_empty_when_parents_list_empty(self) -> None:
        """Test that parent_names is empty when the parents list is empty."""
        product = Product(name="demo", parents=Parents(parent=[]))

        assert product.parent_names == []

    def test_category_names_empty_when_no_categories(self) -> None:
        """Test that category_names is empty when categories is None."""
        assert Product(name="demo").category_names == []

    def test_category_names_empty_when_categories_list_empty(self) -> None:
        """Test that category_names is empty when the categories list is empty."""
        product = Product(name="demo", categories=Categories(category=[]))

        assert product.category_names == []

    def test_docs_list_empty_when_doc_is_none(self) -> None:
        """Test that docs_list is empty when doc is not set."""
        assert Product(name="demo").docs_list == []

    def test_docs_list_empty_when_doc_is_empty_string(self) -> None:
        """Test that docs_list is empty when doc is an empty string."""
        assert Product(name="demo", doc="").docs_list == []

    def test_docs_list_splits_and_strips_comma_separated_values(self) -> None:
        """Test that docs_list splits on commas and strips whitespace/blank items."""
        product = Product(name="demo", doc=" a.md, b.md ,, c.md")

        assert product.docs_list == ["a.md", "b.md", "c.md"]

    def test_build_timestamp_none_when_no_build(self) -> None:
        """Test that build_timestamp is None when there is no build."""
        assert Product(name="demo").build_timestamp is None

    def test_build_timestamp_none_when_timestamp_empty(self) -> None:
        """Test that build_timestamp is None when the build timestamp is empty."""
        product = Product(name="demo", build=Build(timestamp="", branch="", commit=""))

        assert product.build_timestamp is None

    def test_build_timestamp_returns_value_when_set(self) -> None:
        """Test that build_timestamp returns the timestamp when present."""
        product = Product(
            name="demo", build=Build(timestamp="ts", branch="main", commit="abc")
        )

        assert product.build_timestamp == "ts"

    def test_file_path_raises_without_build(self) -> None:
        """Test that file_path raises ValueError when build is missing."""
        with pytest.raises(ValueError, match="Build information is required"):
            _ = Product(name="demo").file_path

    def test_file_path_uses_branch_name_and_commit(self) -> None:
        """Test that file_path is built from branch, name, and commit."""
        product = Product(
            name="demo", build=Build(timestamp="ts", branch="main", commit="abc123")
        )

        assert product.file_path == Path("main/demo/demo_abc123.json")


class TestFromXml:
    """Test cases for Product.from_xml and from_xml_file."""

    def test_from_xml_parses_minimal_product(self) -> None:
        """Test that a minimal XML product is parsed correctly."""
        xml = '<product name="demo" version="1.2.3"/>'

        product = Product.from_xml(xml)

        assert product.name == "demo"
        assert product.version == Version("1.2.3")

    def test_from_xml_parses_nested_parents_and_categories(self) -> None:
        """Test that nested parents/categories elements are parsed."""
        xml = (
            "<product name='demo'>"
            "<parents><parent name='p1'/><parent name='p2'/></parents>"
            "<categories><category name='c1'/></categories>"
            "</product>"
        )

        product = Product.from_xml(xml)

        assert product.parent_names == ["p1", "p2"]
        assert product.category_names == ["c1"]

    def test_from_xml_invalid_content_raises_value_error(self) -> None:
        """Test that malformed XML raises a ValueError."""
        with pytest.raises(ValueError, match="Invalid XML content"):
            Product.from_xml("<product name='demo'>")

    def test_from_xml_missing_root_element_raises_value_error(self) -> None:
        """Test that a non-'product' root element raises a ValueError."""
        with pytest.raises(ValueError, match="Root element must be 'product'"):
            Product.from_xml("<other name='demo'/>")

    def test_from_xml_missing_name_raises_value_error(self) -> None:
        """Test that a missing name attribute raises a ValueError."""
        with pytest.raises(ValueError, match="Product name is required"):
            Product.from_xml("<product version='1.0'/>")

    def test_from_xml_other_validation_error_propagates(self) -> None:
        """Test that validation errors unrelated to name are re-raised as-is."""
        with pytest.raises(ValidationError):
            Product.from_xml("<product name='demo' version='not-a-version'/>")

    def test_from_xml_file_reads_and_parses(self, tmp_path: Path) -> None:
        """Test that from_xml_file reads content from disk and parses it."""
        xml_path = tmp_path / "product.xml"
        xml_path.write_text('<product name="demo"/>', encoding="utf-8")

        product = Product.from_xml_file(xml_path)

        assert product.name == "demo"

    def test_from_xml_file_missing_file_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """Test that from_xml_file raises FileNotFoundError for a missing file."""
        with pytest.raises(FileNotFoundError, match="XML file not found"):
            Product.from_xml_file(tmp_path / "missing.xml")


class TestFromDict:
    """Test cases for Product.from_dict and its legacy alias normalization."""

    def test_from_dict_requires_name(self) -> None:
        """Test that from_dict raises ValueError when name is missing."""
        with pytest.raises(ValueError, match="Product name is required"):
            Product.from_dict({})

    def test_from_dict_uses_product_type_as_default_type(self) -> None:
        """Test that product_type is used when type is not provided."""
        product = Product.from_dict({"name": "demo", "product_type": "bundle"})

        assert product.type == "bundle"

    def test_from_dict_type_takes_precedence_over_product_type(self) -> None:
        """Test that an explicit type overrides product_type."""
        product = Product.from_dict(
            {"name": "demo", "product_type": "bundle", "type": "solution"}
        )

        assert product.type == "solution"

    def test_from_dict_defaults_type_to_solution(self) -> None:
        """Test that type defaults to 'solution' when neither key is given."""
        product = Product.from_dict({"name": "demo"})

        assert product.type == "solution"

    def test_from_dict_license_takes_precedence_over_license_info(self) -> None:
        """Test that license overrides license_info when both are present."""
        product = Product.from_dict(
            {"name": "demo", "license": "MIT", "license_info": "Apache-2.0"}
        )

        assert product.license == "MIT"

    def test_from_dict_uses_license_info_when_license_absent(self) -> None:
        """Test that license_info is used as a fallback for license."""
        product = Product.from_dict({"name": "demo", "license_info": "Apache-2.0"})

        assert product.license == "Apache-2.0"

    def test_from_dict_joins_docs_list_into_doc_string(self) -> None:
        """Test that a docs list is joined into a comma-separated doc string."""
        product = Product.from_dict({"name": "demo", "docs": ["a.md", "b.md"]})

        assert product.doc == "a.md,b.md"

    def test_from_dict_ignores_empty_docs_list(self) -> None:
        """Test that an empty docs list does not set doc."""
        product = Product.from_dict({"name": "demo", "docs": []})

        assert product.doc is None

    def test_from_dict_builds_build_from_build_details(self) -> None:
        """Test that build_details is converted into the build field."""
        product = Product.from_dict(
            {
                "name": "demo",
                "build_details": {
                    "timestamp": "ts",
                    "branch": "main",
                    "commit": "abc",
                },
            }
        )

        assert product.build == Build(timestamp="ts", branch="main", commit="abc")

    def test_from_dict_build_takes_precedence_over_build_details(self) -> None:
        """Test that an explicit build field is preferred over build_details."""
        product = Product.from_dict(
            {
                "name": "demo",
                "build": {"timestamp": "explicit", "branch": "", "commit": ""},
                "build_details": {
                    "timestamp": "ts",
                    "branch": "main",
                    "commit": "abc",
                },
            }
        )

        assert product.build_timestamp == "explicit"


class TestFromJson:
    """Test cases for Product.from_json and from_json_file."""

    def test_from_json_parses_json_string(self) -> None:
        """Test that a JSON string is parsed into a Product."""
        product = Product.from_json(json.dumps({"name": "demo", "version": "1.0.0"}))

        assert product.name == "demo"
        assert product.version == Version("1.0.0")

    def test_from_json_accepts_already_parsed_dict(self) -> None:
        """Test that a pre-parsed dict is accepted directly."""
        product = Product.from_json({"name": "demo"})

        assert product.name == "demo"

    def test_from_json_invalid_content_raises_value_error(self) -> None:
        """Test that invalid JSON text raises a ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON content"):
            Product.from_json("not-json")

    def test_from_json_non_object_raises_type_error(self) -> None:
        """Test that a JSON array (non-object) raises a TypeError."""
        with pytest.raises(TypeError, match="Expected a JSON object"):
            Product.from_json("[1, 2, 3]")

    def test_from_json_file_reads_and_parses(self, tmp_path: Path) -> None:
        """Test that from_json_file reads content from disk and parses it."""
        json_path = tmp_path / "product.json"
        json_path.write_text(json.dumps({"name": "demo"}), encoding="utf-8")

        product = Product.from_json_file(json_path)

        assert product.name == "demo"

    def test_from_json_file_missing_file_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """Test that from_json_file raises FileNotFoundError for a missing file."""
        with pytest.raises(FileNotFoundError, match="JSON file not found"):
            Product.from_json_file(tmp_path / "missing.json")


class TestMerge:
    """Test cases for Product.merge."""

    def test_merge_raises_on_name_mismatch(self) -> None:
        """Test that merge raises ValueError when product names differ."""
        xml_product = Product(name="demo-xml")
        json_product = Product(name="demo-json")

        with pytest.raises(ValueError, match="Product names don't match"):
            Product.merge(xml_product, json_product)

    def test_merge_prefers_json_values_when_present(self) -> None:
        """Test that JSON field values take precedence when set."""
        xml_product = Product(
            name="demo",
            version="1.0.0",
            doc="xml.md",
            date="2024-01-01",
            type="xml-type",
            license="XML-LICENSE",
            display=LocDisplayMapper(name=LocMapper(en="xml")),
            build=Build(timestamp="xml-ts", branch="xml-branch", commit="xml-commit"),
            parents=["xml-parent"],
            categories=["xml-cat"],
        )
        json_product = Product(
            name="demo",
            version="2.0.0",
            doc="json.md",
            date="2024-02-01",
            type="json-type",
            license="JSON-LICENSE",
            display=LocDisplayMapper(name=LocMapper(en="json")),
            build=Build(timestamp="json-ts", branch="json-branch", commit="json-commit"),
            parents=["json-parent"],
            categories=["json-cat"],
        )

        merged = Product.merge(xml_product, json_product)

        assert merged.name == "demo"
        assert merged.version == Version("2.0.0")
        assert merged.doc == "json.md"
        assert merged.date == "2024-02-01"
        assert merged.type == "json-type"
        assert merged.license == "JSON-LICENSE"
        assert merged.display == json_product.display
        assert merged.build == json_product.build
        assert merged.parent_names == ["json-parent"]
        assert merged.category_names == ["json-cat"]

    def test_merge_falls_back_to_xml_values_when_json_missing(self) -> None:
        """Test that XML values are used when JSON fields are empty/None."""
        xml_product = Product(
            name="demo",
            version="1.0.0",
            doc="xml.md",
            date="2024-01-01",
            type="xml-type",
            license="XML-LICENSE",
            build=Build(timestamp="xml-ts", branch="xml-branch", commit="xml-commit"),
            parents=["xml-parent"],
            categories=["xml-cat"],
        )
        json_product = Product(name="demo", type="")

        merged = Product.merge(xml_product, json_product)

        assert merged.version == Version("1.0.0")
        assert merged.doc == "xml.md"
        assert merged.date == "2024-01-01"
        assert merged.type == "xml-type"
        assert merged.license == "XML-LICENSE"
        assert merged.build == xml_product.build
        assert merged.parent_names == ["xml-parent"]
        assert merged.category_names == ["xml-cat"]


class TestToXml:
    """Test cases for Product.to_xml."""

    def test_to_xml_minimal_product(self) -> None:
        """Test that a minimal product serializes required attributes."""
        xml = Product(name="demo").to_xml()

        assert 'name="demo"' in xml
        assert "<product" in xml

    def test_to_xml_includes_doc_when_present(self) -> None:
        """Test that the doc attribute is included when set."""
        xml = Product(name="demo", doc="a.md").to_xml()

        assert 'doc="a.md"' in xml

    def test_to_xml_includes_build_timestamp_when_present(self) -> None:
        """Test that the build attribute uses the build timestamp."""
        xml = Product(
            name="demo", build=Build(timestamp="ts", branch="b", commit="c")
        ).to_xml()

        assert 'build="ts"' in xml

    def test_to_xml_includes_parents_and_categories(self) -> None:
        """Test that parents and categories elements are rendered."""
        xml = Product(
            name="demo", parents=["p1"], categories=["c1"]
        ).to_xml()

        assert "<parents>" in xml
        assert 'name="p1"' in xml
        assert "<categories>" in xml
        assert 'name="c1"' in xml

    def test_to_xml_omits_parents_when_empty(self) -> None:
        """Test that empty parents/categories are omitted from output."""
        xml = Product(name="demo").to_xml()

        assert "<parents>" not in xml
        assert "<categories>" not in xml


class TestToJson:
    """Test cases for Product.to_json."""

    def test_to_json_minimal_product(self) -> None:
        """Test that a minimal product produces the expected base fields."""
        data = Product(name="demo").to_json()

        assert data["name"] == "demo"
        assert data["version"] == ""
        assert data["date"] == ""
        assert data["type"] == "solution"
        assert data["parents"] == []
        assert data["categories"] == []
        assert "build" not in data
        assert "license" not in data
        assert "display" not in data
        assert "doc" not in data

    def test_to_json_includes_optional_fields_when_set(self) -> None:
        """Test that build, license, display, and doc are included when present."""
        product = Product(
            name="demo",
            doc="a.md",
            license="MIT",
            build=Build(timestamp="ts", branch="b", commit="c"),
            display=LocDisplayMapper(name=LocMapper(en="Demo")),
        )

        data = product.to_json()

        assert data["build"] == {"timestamp": "ts", "branch": "b", "commit": "c"}
        assert data["license"] == "MIT"
        assert data["display"] == {"name": {"en": "Demo"}}
        assert data["doc"] == "a.md"


class TestToToml:
    """Test cases for Product.to_toml."""

    def test_to_toml_contains_name_and_version(self) -> None:
        """Test that the TOML output contains the product's name and version."""
        toml_str = Product(name="demo", version="1.2.3").to_toml()

        assert 'name = "demo"' in toml_str
        assert "1.2.3" in toml_str


class TestExport:
    """Test cases for Product.export."""

    def test_export_xml_writes_file(self, tmp_path: Path) -> None:
        """Test that export('xml', ...) writes the XML representation to disk."""
        product = Product(name="demo")
        destination = tmp_path / "product.xml"

        product.export("xml", destination)

        assert 'name="demo"' in destination.read_text(encoding="utf-8")

    def test_export_toml_writes_file(self, tmp_path: Path) -> None:
        """Test that export('toml', ...) writes the TOML representation to disk."""
        product = Product(name="demo")
        destination = tmp_path / "product.toml"

        product.export("toml", destination)

        assert 'name = "demo"' in destination.read_text(encoding="utf-8")

    def test_export_unsupported_mode_raises_attribute_error(
        self, tmp_path: Path
    ) -> None:
        """Test that an unsupported mode raises AttributeError."""
        product = Product(name="demo")

        with pytest.raises(AttributeError):
            product.export("yaml", tmp_path / "product.yaml")  # type: ignore[arg-type]
