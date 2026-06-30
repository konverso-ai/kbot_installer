"""Tests for ProductInstallable and Product integration."""

import json
import tempfile
from pathlib import Path

import pytest

from installable import create_installable
from installable.product_installable import ProductInstallable
from utils.product import Product
from utils.version import Version


def _version_str(value: str) -> str:
    return Version(value).to_str()


def _installable_from_json(json_content: str) -> ProductInstallable:
    data = json.loads(json_content)
    return ProductInstallable(product=Product.from_json(data), env=data.get("env", "dev"))


def _installable_from_xml(xml_content: str) -> ProductInstallable:
    return ProductInstallable(product=Product.from_xml(xml_content))


class TestProduct:
    """Test cases for Product class."""

    def test_initialization(self) -> None:
        """Test Product initialization."""
        product = create_installable(
            name="test",
            version="1.0.0",
            product_type="solution",
            parents=["parent1"],
            categories=["cat1"],
        )

        assert product.name == "test"
        assert product.version == _version_str("1.0.0")
        assert product.type == "solution"
        assert product.parents == ["parent1"]
        assert product.categories == ["cat1"]

    def test_initialization_minimal(self) -> None:
        """Test Product initialization with minimal parameters."""
        product = create_installable(name="test")

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
        product = _installable_from_xml(xml_content)

        assert product.name == "jira"
        assert product.version == _version_str("2025.02")
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
        product = _installable_from_xml(xml_content)

        assert product.name == "jira"
        assert product.parents == ["ithd", "kbot"]
        assert product.categories == ["itsm", "knowledge"]

    def test_from_xml_with_doc(self) -> None:
        """Test creating Product from XML with doc attribute."""
        xml_content = """
        <product name="jira" version="2025.02" type="solution" doc="doc1,doc2,doc3">
        </product>
        """
        product = _installable_from_xml(xml_content)

        assert product.name == "jira"
        assert product.docs == ["doc1", "doc2", "doc3"]

    def test_from_xml_with_empty_doc(self) -> None:
        """Test creating Product from XML with empty doc attribute."""
        xml_content = """
        <product name="jira" version="2025.02" type="solution" doc="">
        </product>
        """
        product = _installable_from_xml(xml_content)

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
        product = _installable_from_json(json_content)

        assert product.name == "jira"
        assert product.version == _version_str("2025.03")
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
        product = _installable_from_json(json_content)

        assert product.name == "jira"
        assert product.version == _version_str("2025.03")
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
        product = _installable_from_json(json_content)

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
            product = ProductInstallable(product=Product.from_xml_file(xml_path))
            assert product.name == "test"
            assert product.version == _version_str("1.0.0")
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
            product = ProductInstallable(product=Product.from_json_file(json_path))
            assert product.name == "test"
            assert product.version == _version_str("1.0.0")
        finally:
            Path(json_path).unlink()

    def test_merge_xml_json(self) -> None:
        """Test merging XML and JSON products."""
        xml_product = create_installable(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
        )

        json_product = create_installable(
            name="jira",
            version="2025.03",  # Different version
            type="solution",
            parents=[],  # Empty parents
            categories=["itsm", "knowledge"],  # Additional category
            license="kbot-included",
            display={"name": {"en": "Kbot for Atlassian"}},
        )

        merged_product = Product.merge(xml_product.product, json_product.product)
        merged = ProductInstallable(
            product=merged_product,
            env=json_product.env,
            branch=json_product.branch or xml_product.branch,
        )

        assert merged.name == "jira"
        assert merged.version == _version_str("2025.03")  # JSON takes precedence
        assert merged.parents == ["ithd"]  # JSON empty, so XML is used
        assert merged.categories == ["itsm", "knowledge"]  # JSON takes precedence
        assert merged.license == "kbot-included"  # From JSON
        assert merged.display["name"]["en"] == "Kbot for Atlassian"  # From JSON

    def test_merge_xml_json_different_names(self) -> None:
        """Test merging products with different names."""
        xml_product = create_installable(name="jira", version="1.0.0", type="solution")
        json_product = create_installable(
            name="confluence", version="1.0.0", type="solution"
        )

        with pytest.raises(ValueError, match="Product names don't match"):
            Product.merge(xml_product.product, json_product.product)

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

            product = create_installable(name="jira")
            product.load_from_installer_folder(product_dir)
            assert product.name == "jira"
            assert product.version == _version_str("2025.02")

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

            product = create_installable(name="jira")
            product.load_from_installer_folder(product_dir)
            assert product.name == "jira"
            assert product.version == _version_str("2025.03")  # From JSON
            assert product.parents == ["ithd"]  # From XML
            assert product.license == "kbot-included"  # From JSON

    def test_to_xml(self) -> None:
        """Test converting Product to XML."""
        product = create_installable(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
            docs=["doc1", "doc2"],
        )

        xml = product.to_xml()
        assert 'name="jira"' in xml
        assert 'version="{}"'.format(_version_str("2025.02")) in xml
        assert 'type="solution"' in xml
        assert 'name="ithd"' in xml
        assert 'name="itsm"' in xml
        assert 'doc="doc1,doc2"' in xml

    def test_to_json(self) -> None:
        """Test converting Product to JSON."""
        product = create_installable(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
            docs=["doc1", "doc2"],
            env="prod",
            license="kbot-included",
        )

        data = product.to_json()

        assert data["name"] == "jira"
        assert data["version"] == "2025.02"
        assert data["type"] == "solution"
        assert data["parents"] == ["ithd"]
        assert data["categories"] == ["itsm"]
        assert data["doc"] == "doc1,doc2"
        assert data["env"] == "prod"
        assert data["license"] == "kbot-included"

    def test_to_json_description_structure(self) -> None:
        """Test Product.to_json matches description.json structure."""
        json_content = """
        {
            "name": "3rdparty",
            "version": "2025.03",
            "date": "2026/06/17",
            "type": "framework",
            "parents": [],
            "categories": [],
            "build": {
                "timestamp": "2026/06/17 07:08:54",
                "branch": "release-2025.03-dev",
                "commit": "70ca3093f81fe9ffc5f22a572ff86dd038e6cb7f"
            },
            "license": "kbot-included",
            "display": {
                "name": {
                    "en": "",
                    "fr": ""
                },
                "description": {
                    "en": "",
                    "fr": ""
                }
            }
        }
        """
        product = Product.from_json(json_content)
        assert product.to_json() == json.loads(json_content)

    def test_str_representation(self) -> None:
        """Test string representation of ProductInstallable."""
        product = create_installable(name="jira", version="2025.02", type="solution")
        assert (
            str(product)
            == f"ProductInstallable(name='jira', version='{_version_str('2025.02')}', type='solution')"
        )

    def test_repr_representation(self) -> None:
        """Test detailed string representation of ProductInstallable."""
        product = create_installable(
            name="jira",
            version="2025.02",
            type="solution",
            parents=["ithd"],
            categories=["itsm"],
        )
        expected = (
            f"ProductInstallable(name='jira', version='{_version_str('2025.02')}', "
            "type='solution', parents=['ithd'], categories=['itsm'])"
        )
        assert repr(product) == expected

    def test_parse_comma_separated_string(self) -> None:
        """Test _parse_comma_separated_string static method."""
        # Test with normal string
        result = ProductInstallable._parse_comma_separated_string("doc1,doc2,doc3")
        assert result == ["doc1", "doc2", "doc3"]

        # Test with spaces
        result = ProductInstallable._parse_comma_separated_string("doc1, doc2 , doc3")
        assert result == ["doc1", "doc2", "doc3"]

        # Test with empty string
        result = ProductInstallable._parse_comma_separated_string("")
        assert result == []

        # Test with None (should be handled gracefully)
        result = ProductInstallable._parse_comma_separated_string(None)
        assert result == []

        # Test with empty elements
        result = ProductInstallable._parse_comma_separated_string("doc1,,doc2, ,doc3")
        assert result == ["doc1", "doc2", "doc3"]

    def test_load_product_by_name(self) -> None:
        """Test _load_product_by_name method."""
        product = create_installable(name="test", version="1.0.0")
        loaded_product = product._load_product_by_name("new-product")

        assert loaded_product.name == "new-product"
        # Version inherits from parent product
        assert loaded_product.version == _version_str("1.0.0")

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
            product = create_installable(name="jira")
            product.load_from_installer_folder(product_dir)

            assert product.name == "jira"  # Should remain unchanged
            assert product.version == _version_str("2025.03")  # From JSON
            assert product.parents == ["ithd"]  # From XML
            assert product.docs == ["doc1", "doc2"]  # From XML
            assert product.env == "prod"  # From JSON
            assert product.license == "kbot-included"  # From JSON

    def test_get_dependencies(self) -> None:
        """Test get_dependencies method."""
        # Create a product with dependencies
        product_a = create_installable(
            name="product-a", version="1.0.0", parents=["product-b", "product-c"]
        )
        product_b = create_installable(
            name="product-b", version="1.0.0", parents=["product-d"]
        )
        product_c = create_installable(name="product-c", version="1.0.0")
        product_d = create_installable(name="product-d", version="1.0.0")

        # Mock the _load_product_by_name method to return our test products
        def mock_load_product(
            name: str,
            base_path=None,  # noqa: ARG001
            default_version=None,  # noqa: ARG001
        ) -> ProductInstallable:
            products = {
                "product-b": product_b,
                "product-c": product_c,
                "product-d": product_d,
            }
            return products.get(name, create_installable(name=name))

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

    def test_download_without_dependencies(self) -> None:
        """Test download method without dependencies."""
        from unittest.mock import Mock, patch

        product = create_installable(name="test-product", version="1.0.0")
        mock_provider = Mock()
        mock_provider.get_name.return_value = "nexus"
        mock_provider.get_branch.return_value = "master"
        product.provider = mock_provider

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            product_path = base_path / "test-product"
            # Create description.xml to simulate successful clone
            product_path.mkdir(parents=True)
            (product_path / "description.xml").write_text("<product></product>")

            with patch.object(
                product, "load_from_installer_folder"
            ) as mock_load_folder:
                product.download(base_path, dependencies=False)

                # Verify provider.clone_and_checkout was called with product subdirectory
                from installer_support.installer_utils import version_to_branch

                branch = version_to_branch(product.version, env="dev")
                mock_provider.clone_and_checkout.assert_called_once_with(
                    product_path, branch, repository_name="test-product"
                )
                # Verify load_from_installer_folder was called
                mock_load_folder.assert_called_once_with(product_path)

    def test_download_with_dependencies(self) -> None:
        """Test download method with dependencies."""
        from unittest.mock import Mock, patch

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create products with dependencies
            product_a = create_installable(
                name="product-a", version="1.0.0", parents=["product-b"]
            )
            product_b = create_installable(name="product-b", version="1.0.0")

            # Mock providers
            mock_provider_a = Mock()
            mock_provider_a.get_name.return_value = "nexus"
            mock_provider_a.get_branch.return_value = "master"
            mock_provider_b = Mock()
            mock_provider_b.get_name.return_value = "github"
            mock_provider_b.get_branch.return_value = "main"
            product_a.provider = mock_provider_a
            product_b.provider = mock_provider_b

            # Mock _load_product_by_name to return product_b
            def mock_load_product(
                name: str,
                base_path=None,  # noqa: ARG001
                default_version=None,  # noqa: ARG001
            ) -> ProductInstallable:
                if name == "product-b":
                    return product_b
                return create_installable(name=name)

            product_a._load_product_by_name = mock_load_product

            # Mock load_from_installer_folder
            with (
                patch.object(product_a, "load_from_installer_folder") as mock_load_a,
                patch.object(product_b, "load_from_installer_folder") as mock_load_b,
            ):
                base_path = Path(temp_dir)
                product_a_path = base_path / "product-a"
                product_b_path = base_path / "product-b"
                # Create description.xml files to simulate successful clone
                product_a_path.mkdir(parents=True)
                product_b_path.mkdir(parents=True)
                (product_a_path / "description.xml").write_text("<product></product>")
                (product_b_path / "description.xml").write_text("<product></product>")

                product_a.download(base_path, dependencies=True)

                # Verify both providers were called (version converted to branch)
                from installer_support.installer_utils import version_to_branch

                branch_a = version_to_branch(product_a.version, env="dev")
                branch_b = version_to_branch(product_b.version, env="dev")
                mock_provider_a.clone_and_checkout.assert_called_once_with(
                    product_a_path, branch_a, repository_name="product-a"
                )
                mock_provider_b.clone_and_checkout.assert_called_once_with(
                    product_b_path, branch_b, repository_name="product-b"
                )

                # Verify load_from_installer_folder was called for both
                assert mock_load_a.call_count == 1
                assert mock_load_b.call_count == 1

    def test_download_with_dependencies_same_product_name(self) -> None:
        """Test download when dependency has same name uses base path."""
        from unittest.mock import Mock, patch

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create product with self as dependency (shouldn't happen but tests path logic)
            product_a = create_installable(
                name="product-a", version="1.0.0", parents=["product-b"]
            )
            product_b = create_installable(name="product-b", version="1.0.0")

            # Mock providers
            mock_provider_a = Mock()
            mock_provider_a.get_name.return_value = "nexus"
            mock_provider_a.get_branch.return_value = "master"
            mock_provider_b = Mock()
            mock_provider_b.get_name.return_value = "github"
            mock_provider_b.get_branch.return_value = "main"
            product_a.provider = mock_provider_a
            product_b.provider = mock_provider_b

            # Mock _load_product_by_name
            def mock_load_product(
                name: str,
                base_path=None,  # noqa: ARG001
                default_version=None,  # noqa: ARG001
            ) -> ProductInstallable:
                if name == "product-b":
                    return product_b
                return create_installable(name=name)

            product_a._load_product_by_name = mock_load_product

            # Mock load_from_installer_folder
            with (
                patch.object(product_a, "load_from_installer_folder") as mock_load_a,
                patch.object(product_b, "load_from_installer_folder") as mock_load_b,
            ):
                base_path = Path(temp_dir)
                product_a_path = base_path / "product-a"
                product_b_path = base_path / "product-b"
                # Create description.xml files to simulate successful clone
                product_a_path.mkdir(parents=True)
                product_b_path.mkdir(parents=True)
                (product_a_path / "description.xml").write_text("<product></product>")
                (product_b_path / "description.xml").write_text("<product></product>")

                product_a.download(base_path, dependencies=True)

                # When cloning product_a in collection, if name matches, use original path
                # Otherwise use parent / product.name
                from installer_support.installer_utils import version_to_branch

                branch_a = version_to_branch(product_a.version, env="dev")
                mock_provider_a.clone_and_checkout.assert_called_once_with(
                    product_a_path, branch_a, repository_name="product-a"
                )
                # product-b should be cloned to base_path / "product-b"
                branch_b = version_to_branch(product_b.version, env="dev")
                mock_provider_b.clone_and_checkout.assert_called_once_with(
                    product_b_path, branch_b, repository_name="product-b"
                )

                assert mock_load_a.call_count == 1
                assert mock_load_b.call_count == 1
