"""Tests for Product class."""

import json
import tempfile
from pathlib import Path

import pytest

from kbot_installer.core.product.product import Product


class TestProduct:
    """Test cases for Product class."""

    def test_initialization(self) -> None:
        """Test Product initialization."""
        product = Product(
            name="test",
            version="1.0.0",
            type="solution",
            parents=["parent1"],
            categories=["cat1"],
        )

        assert product.name == "test"
        assert product.version == "1.0.0"
        assert product.type == "solution"
        assert product.parents == ["parent1"]
        assert product.categories == ["cat1"]

    def test_initialization_minimal(self) -> None:
        """Test Product initialization with minimal parameters."""
        product = Product(name="test")

        assert product.name == "test"
        assert product.version == ""  # Default empty string
        assert product.type == "solution"  # Default
        assert product.parents == []  # Default empty list
        assert product.categories == []  # Default empty list
        assert product.docs == []  # Default empty list
        assert product.env == "dev"  # Default

    def test_from_xml_simple(self) -> None:
        """Test creating Product from simple XML."""
        xml_content = """
        <product name="jira" version="2025.02" type="solution">
        </product>
        """
        product = Product.from_xml(xml_content)

        assert product.name == "jira"
        assert product.version == "2025.02"
        assert product.type == "solution"
        assert product.parents == []
        assert product.categories == []

    def test_from_xml_with_parents_and_categories(self) -> None:
        """Test creating Product from XML with parents and categories."""
        xml_content = """
        <product name="jira" version="2025.02" type="solution">
            <parents>
                <parent name="ithd"/>
                <parent name="kbot"/>
            </parents>
            <categories>
                <category name="itsm"/>
                <category name="knowledge"/>
            </categories>
        </product>
        """
        product = Product.from_xml(xml_content)

        assert product.name == "jira"
        assert product.parents == ["ithd", "kbot"]
        assert product.categories == ["itsm", "knowledge"]

    def test_from_xml_with_doc(self) -> None:
        """Test creating Product from XML with doc attribute."""
        xml_content = """
        <product name="jira" version="2025.02" type="solution" doc="doc1,doc2,doc3">
        </product>
        """
        product = Product.from_xml(xml_content)

        assert product.name == "jira"
        assert product.docs == ["doc1", "doc2", "doc3"]

    def test_from_xml_with_empty_doc(self) -> None:
        """Test creating Product from XML with empty doc attribute."""
        xml_content = """
        <product name="jira" version="2025.02" type="solution" doc="">
        </product>
        """
        product = Product.from_xml(xml_content)

        assert product.name == "jira"
        assert product.docs == []

    def test_from_xml_invalid_xml(self) -> None:
        """Test creating Product from invalid XML."""
        xml_content = "<invalid>test</invalid>"
        with pytest.raises(ValueError, match="Root element must be 'product'"):
            Product.from_xml(xml_content)

    def test_from_xml_missing_name(self) -> None:
        """Test creating Product from XML without name."""
        xml_content = '<product version="1.0.0"></product>'
        with pytest.raises(ValueError, match="Product name is required"):
            Product.from_xml(xml_content)

    def test_from_json_simple(self) -> None:
        """Test creating Product from simple JSON."""
        json_content = """
        {
            "name": "jira",
            "version": "2025.03",
            "type": "solution"
        }
        """
        product = Product.from_json(json_content)

        assert product.name == "jira"
        assert product.version == "2025.03"
        assert product.type == "solution"

    def test_from_json_complex(self) -> None:
        """Test creating Product from complex JSON."""
        json_content = """
        {
            "name": "jira",
            "version": "2025.03",
            "type": "solution",
            "parents": ["ithd"],
            "categories": ["itsm", "knowledge"],
            "doc": "doc1,doc2,doc3",
            "env": "prod",
            "license": "kbot-included",
            "display": {
                "name": {
                    "en": "Kbot for Atlassian",
                    "fr": "Kbot pour Atlassian"
                }
            },
            "build": {
                "timestamp": "2025/09/29 14:08:06",
                "branch": "release-2025.03-dev",
                "commit": "7062432bd6ebeb174bf38bc5dde8d75d6e603e09"
            }
        }
        """
        product = Product.from_json(json_content)

        assert product.name == "jira"
        assert product.version == "2025.03"
        assert product.parents == ["ithd"]
        assert product.categories == ["itsm", "knowledge"]
        assert product.docs == ["doc1", "doc2", "doc3"]
        assert product.env == "prod"
        assert product.license == "kbot-included"
        assert product.display["name"]["en"] == "Kbot for Atlassian"
        assert product.build_details["timestamp"] == "2025/09/29 14:08:06"

    def test_from_json_with_empty_doc(self) -> None:
        """Test creating Product from JSON with empty doc."""
        json_content = """
        {
            "name": "jira",
            "version": "2025.03",
            "doc": ""
        }
        """
        product = Product.from_json(json_content)

        assert product.name == "jira"
        assert product.docs == []

    def test_from_json_invalid_json(self) -> None:
        """Test creating Product from invalid JSON."""
        json_content = '{"name": "test"'  # Missing closing brace
        with pytest.raises(ValueError, match="Invalid JSON content"):
            Product.from_json(json_content)

    def test_from_json_missing_name(self) -> None:
        """Test creating Product from JSON without name."""
        json_content = '{"version": "1.0.0"}'
        with pytest.raises(ValueError, match="Product name is required"):
            Product.from_json(json_content)

    def test_from_xml_file(self) -> None:
        """Test creating Product from XML file."""
        xml_content = """
        <product name="test" version="1.0.0" type="solution">
        </product>
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            xml_path = f.name

        try:
            product = Product.from_xml_file(xml_path)
            assert product.name == "test"
            assert product.version == "1.0.0"
        finally:
            Path(xml_path).unlink()

    def test_from_xml_file_not_found(self) -> None:
        """Test creating Product from non-existent XML file."""
        with pytest.raises(FileNotFoundError):
            Product.from_xml_file("/non/existent/file.xml")

    def test_from_json_file(self) -> None:
        """Test creating Product from JSON file."""
        json_content = '{"name": "test", "version": "1.0.0", "type": "solution"}'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_content)
            json_path = f.name

        try:
            product = Product.from_json_file(json_path)
            assert product.name == "test"
            assert product.version == "1.0.0"
        finally:
            Path(json_path).unlink()

    def test_merge_xml_json(self) -> None:
        """Test merging XML and JSON products."""
        xml_product = Product(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
        )

        json_product = Product(
            name="jira",
            version="2025.03",  # Different version
            type="solution",
            parents=[],  # Empty parents
            categories=["itsm", "knowledge"],  # Additional category
            license="kbot-included",
            display={"name": {"en": "Kbot for Atlassian"}},
        )

        merged = Product.merge_xml_json(xml_product, json_product)

        assert merged.name == "jira"
        assert merged.version == "2025.03"  # JSON takes precedence
        assert merged.parents == ["ithd"]  # JSON empty, so XML is used
        assert merged.categories == ["itsm", "knowledge"]  # JSON takes precedence
        assert merged.license == "kbot-included"  # From JSON
        assert merged.display["name"]["en"] == "Kbot for Atlassian"  # From JSON

    def test_merge_xml_json_different_names(self) -> None:
        """Test merging products with different names."""
        xml_product = Product(name="jira", version="1.0.0", type="solution")
        json_product = Product(name="confluence", version="1.0.0", type="solution")

        with pytest.raises(ValueError, match="Product names don't match"):
            Product.merge_xml_json(xml_product, json_product)

    def test_from_installer_folder_xml_only(self) -> None:
        """Test creating Product from installer folder with XML only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "jira"
            product_dir.mkdir()

            xml_content = """
            <product name="jira" version="2025.02" type="solution">
            </product>
            """
            xml_file = product_dir / "description.xml"
            xml_file.write_text(xml_content)

            product = Product(name="jira")
            product.load_from_installer_folder(product_dir)
            assert product.name == "jira"
            assert product.version == "2025.02"

    def test_from_installer_folder_xml_and_json(self) -> None:
        """Test creating Product from installer folder with XML and JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "jira"
            product_dir.mkdir()

            xml_content = """
            <product name="jira" version="2025.02" type="solution">
                <parents><parent name="ithd"/></parents>
            </product>
            """
            xml_file = product_dir / "description.xml"
            xml_file.write_text(xml_content)

            json_content = """
            {
                "name": "jira",
                "version": "2025.03",
                "license": "kbot-included",
                "display": {
                    "name": {"en": "Kbot for Atlassian"}
                }
            }
            """
            json_file = product_dir / "description.json"
            json_file.write_text(json_content)

            product = Product(name="jira")
            product.load_from_installer_folder(product_dir)
            assert product.name == "jira"
            assert product.version == "2025.03"  # From JSON
            assert product.parents == ["ithd"]  # From XML
            assert product.license == "kbot-included"  # From JSON

    def test_to_xml(self) -> None:
        """Test converting Product to XML."""
        product = Product(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
            docs=["doc1", "doc2"],
        )

        xml = product.to_xml()
        assert '<product name="jira"' in xml
        assert 'version="2025.02"' in xml
        assert 'type="solution"' in xml
        assert '<parent name="ithd" />' in xml
        assert '<category name="itsm" />' in xml
        assert 'doc="doc1,doc2"' in xml

    def test_to_json(self) -> None:
        """Test converting Product to JSON."""
        product = Product(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
            docs=["doc1", "doc2"],
            env="prod",
            license="kbot-included",
        )

        json_str = product.to_json()
        data = json.loads(json_str)

        assert data["name"] == "jira"
        assert data["version"] == "2025.02"
        assert data["type"] == "solution"
        assert data["parents"] == ["ithd"]
        assert data["categories"] == ["itsm"]
        assert data["doc"] == "doc1,doc2"
        assert data["env"] == "prod"
        assert data["license"] == "kbot-included"

    def test_str_representation(self) -> None:
        """Test string representation of Product."""
        product = Product(name="jira", version="2025.02", type="solution")
        assert (
            str(product) == "Product(name='jira', version='2025.02', type='solution')"
        )

    def test_repr_representation(self) -> None:
        """Test detailed string representation of Product."""
        product = Product(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
        )
        expected = "Product(name='jira', version='2025.02', type='solution', parents=['ithd'], categories=['itsm'])"
        assert repr(product) == expected

    def test_parse_comma_separated_string(self) -> None:
        """Test _parse_comma_separated_string static method."""
        # Test with normal string
        result = Product._parse_comma_separated_string("doc1,doc2,doc3")
        assert result == ["doc1", "doc2", "doc3"]

        # Test with spaces
        result = Product._parse_comma_separated_string("doc1, doc2 , doc3")
        assert result == ["doc1", "doc2", "doc3"]

        # Test with empty string
        result = Product._parse_comma_separated_string("")
        assert result == []

        # Test with None (should be handled gracefully)
        result = Product._parse_comma_separated_string(None)
        assert result == []

        # Test with empty elements
        result = Product._parse_comma_separated_string("doc1,,doc2, ,doc3")
        assert result == ["doc1", "doc2", "doc3"]

    def test_load_product_by_name(self) -> None:
        """Test _load_product_by_name method."""
        product = Product(name="test", version="1.0.0")
        loaded_product = product._load_product_by_name("new-product")

        assert loaded_product.name == "new-product"
        assert loaded_product.version == ""  # Default empty string

    def test_update_from_product(self) -> None:
        """Test _update_from_product method."""
        source_product = Product(
            name="source",
            version="2.0.0",
            build="build123",
            date="2025-01-01",
            type="framework",
            docs=["doc1", "doc2"],
            env="prod",
            parents=["parent1", "parent2"],
            categories=["cat1"],
            license="MIT",
            display={"name": {"en": "Source Product"}},
            build_details={"timestamp": "2025-01-01"},
        )

        target_product = Product(name="target", version="1.0.0")
        target_product._update_from_product(source_product)

        # Check that all fields are updated except name and provider
        assert target_product.name == "target"  # Should remain unchanged
        assert target_product.version == "2.0.0"
        assert target_product.build == "build123"
        assert target_product.date == "2025-01-01"
        assert target_product.type == "framework"
        assert target_product.docs == ["doc1", "doc2"]
        assert target_product.env == "prod"
        assert target_product.parents == ["parent1", "parent2"]
        assert target_product.categories == ["cat1"]
        assert target_product.license == "MIT"
        assert target_product.display == {"name": {"en": "Source Product"}}
        assert target_product.build_details == {"timestamp": "2025-01-01"}

    def test_load_from_installer_folder(self) -> None:
        """Test load_from_installer_folder method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "jira"
            product_dir.mkdir()

            xml_content = """
            <product name="jira" version="2025.02" type="solution" doc="doc1,doc2">
                <parents><parent name="ithd"/></parents>
            </product>
            """
            xml_file = product_dir / "description.xml"
            xml_file.write_text(xml_content)

            json_content = """
            {
                "name": "jira",
                "version": "2025.03",
                "env": "prod",
                "license": "kbot-included"
            }
            """
            json_file = product_dir / "description.json"
            json_file.write_text(json_content)

            # Create a product instance and load data into it
            product = Product(name="jira")
            product.load_from_installer_folder(product_dir)

            assert product.name == "jira"  # Should remain unchanged
            assert product.version == "2025.03"  # From JSON
            assert product.parents == ["ithd"]  # From XML
            assert product.docs == ["doc1", "doc2"]  # From XML
            assert product.env == "prod"  # From JSON
            assert product.license == "kbot-included"  # From JSON

    def test_get_dependencies(self) -> None:
        """Test get_dependencies method."""
        # Create a product with dependencies
        product_a = Product(name="product-a", version="1.0.0", parents=["product-b", "product-c"])
        product_b = Product(name="product-b", version="1.0.0", parents=["product-d"])
        product_c = Product(name="product-c", version="1.0.0")
        product_d = Product(name="product-d", version="1.0.0")

        # Mock the _load_product_by_name method to return our test products
        def mock_load_product(name: str) -> Product:
            products = {"product-b": product_b, "product-c": product_c, "product-d": product_d}
            return products.get(name, Product(name=name))

        product_a._load_product_by_name = mock_load_product

        # Get dependencies collection
        collection = product_a.get_dependencies()

        # Check that we get all products in BFS order
        assert len(collection.products) == 4
        product_names = [p.name for p in collection.products]

        # BFS order should be: product-a, product-b, product-c, product-d
        # (product-a first, then its direct dependencies, then their dependencies)
        assert product_names[0] == "product-a"
        assert "product-b" in product_names
        assert "product-c" in product_names
        assert "product-d" in product_names
