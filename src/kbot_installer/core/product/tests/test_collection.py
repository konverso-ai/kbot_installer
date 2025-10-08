"""Tests for collection module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kbot_installer.core.product.collection import ProductCollection
from kbot_installer.core.product.product import Product


class TestProductCollection:
    """Test cases for ProductCollection class."""

    @pytest.fixture
    def sample_products(self) -> list[Product]:
        """Create sample products for testing."""
        return [
            Product(
                name="product1",
                version="1.0.0",
                type="solution",
                parents=["parent1"],
                categories=["category1", "category2"],
                build="build1",
                date="2023-01-01",
                license="MIT",
            ),
            Product(
                name="product2",
                version="2.0.0",
                type="framework",
                parents=[],
                categories=["category2", "category3"],
                build="build2",
                date="2023-02-01",
                license="Apache",
            ),
            Product(
                name="product3",
                version="3.0.0",
                type="customer",
                parents=["product1"],
                categories=["category1"],
                build="build3",
                date="2023-03-01",
                license="GPL",
            ),
        ]

    @pytest.fixture
    def empty_collection(self) -> ProductCollection:
        """Create an empty ProductCollection."""
        return ProductCollection()

    @pytest.fixture
    def populated_collection(self, sample_products) -> ProductCollection:
        """Create a ProductCollection with sample products."""
        return ProductCollection(sample_products)

    def test_initialization_empty(self, empty_collection) -> None:
        """Test initialization with no products."""
        assert empty_collection.products == []

    def test_initialization_with_products(
        self, sample_products, populated_collection
    ) -> None:
        """Test initialization with products."""
        assert len(populated_collection.products) == 3
        assert populated_collection.products == sample_products

    def test_initialization_with_none(self) -> None:
        """Test initialization with None products."""
        collection = ProductCollection(None)
        assert collection.products == []

    def test_add_product(self, empty_collection, sample_products) -> None:
        """Test adding a product to the collection."""
        product = sample_products[0]
        empty_collection.add_product(product)

        assert len(empty_collection.products) == 1
        assert empty_collection.products[0] == product

    def test_add_multiple_products(self, empty_collection, sample_products) -> None:
        """Test adding multiple products to the collection."""
        for product in sample_products:
            empty_collection.add_product(product)

        assert len(empty_collection.products) == 3
        assert empty_collection.products == sample_products

    def test_remove_product_existing(self, populated_collection) -> None:
        """Test removing an existing product."""
        result = populated_collection.remove_product("product1")

        assert result is True
        assert len(populated_collection.products) == 2
        assert populated_collection.get_product("product1") is None

    def test_remove_product_nonexistent(self, populated_collection) -> None:
        """Test removing a non-existent product."""
        result = populated_collection.remove_product("nonexistent")

        assert result is False
        assert len(populated_collection.products) == 3

    def test_get_product_existing(self, populated_collection) -> None:
        """Test getting an existing product."""
        product = populated_collection.get_product("product1")

        assert product is not None
        assert product.name == "product1"
        assert product.version == "1.0.0"

    def test_get_product_nonexistent(self, populated_collection) -> None:
        """Test getting a non-existent product."""
        product = populated_collection.get_product("nonexistent")

        assert product is None

    def test_get_all_products(self, populated_collection, sample_products) -> None:
        """Test getting all products."""
        products = populated_collection.get_all_products()

        assert products == sample_products
        # Verify it returns a copy, not a reference
        assert products is not populated_collection.products

    def test_get_products_by_type(self, populated_collection) -> None:
        """Test filtering products by type."""
        solution_products = populated_collection.get_products_by_type("solution")
        framework_products = populated_collection.get_products_by_type("framework")
        customer_products = populated_collection.get_products_by_type("customer")

        assert len(solution_products) == 1
        assert solution_products[0].name == "product1"

        assert len(framework_products) == 1
        assert framework_products[0].name == "product2"

        assert len(customer_products) == 1
        assert customer_products[0].name == "product3"

    def test_get_products_by_type_nonexistent(self, populated_collection) -> None:
        """Test filtering products by non-existent type."""
        products = populated_collection.get_products_by_type("nonexistent")

        assert products == []

    def test_get_products_by_category(self, populated_collection) -> None:
        """Test filtering products by category."""
        category1_products = populated_collection.get_products_by_category("category1")
        category2_products = populated_collection.get_products_by_category("category2")
        category3_products = populated_collection.get_products_by_category("category3")

        assert len(category1_products) == 2  # product1 and product3
        assert len(category2_products) == 2  # product1 and product2
        assert len(category3_products) == 1  # product2

    def test_get_products_by_category_nonexistent(self, populated_collection) -> None:
        """Test filtering products by non-existent category."""
        products = populated_collection.get_products_by_category("nonexistent")

        assert products == []

    def test_get_product_names(self, populated_collection) -> None:
        """Test getting all product names."""
        names = populated_collection.get_product_names()

        assert names == ["product1", "product2", "product3"]

    def test_filter_products_by_type(self, populated_collection) -> None:
        """Test filtering products by type using filter_products."""
        solution_products = populated_collection.filter_products(type="solution")

        assert len(solution_products) == 1
        assert solution_products[0].name == "product1"

    def test_filter_products_by_category(self, populated_collection) -> None:
        """Test filtering products by category using filter_products."""
        category1_products = populated_collection.filter_products(category="category1")

        assert len(category1_products) == 2
        assert all("category1" in p.categories for p in category1_products)

    def test_filter_products_has_parents_true(self, populated_collection) -> None:
        """Test filtering products that have parents."""
        products_with_parents = populated_collection.filter_products(has_parents=True)

        assert len(products_with_parents) == 2
        assert all(p.parents for p in products_with_parents)

    def test_filter_products_has_parents_false(self, populated_collection) -> None:
        """Test filtering products that don't have parents."""
        products_without_parents = populated_collection.filter_products(
            has_parents=False
        )

        assert len(products_without_parents) == 1
        assert not products_without_parents[0].parents

    def test_filter_products_multiple_filters(self, populated_collection) -> None:
        """Test filtering products with multiple criteria."""
        products = populated_collection.filter_products(
            type="solution", category="category1"
        )

        assert len(products) == 1
        assert products[0].name == "product1"

    def test_filter_products_no_filters(self, populated_collection) -> None:
        """Test filtering products with no filters."""
        products = populated_collection.filter_products()

        assert products == populated_collection.products

    def test_iteration(self, populated_collection, sample_products) -> None:
        """Test iteration over products."""
        products = list(populated_collection)

        assert products == sample_products

    def test_length(self, populated_collection) -> None:
        """Test length of collection."""
        assert len(populated_collection) == 3

    def test_contains_existing(self, populated_collection) -> None:
        """Test contains with existing product."""
        assert "product1" in populated_collection

    def test_contains_nonexistent(self, populated_collection) -> None:
        """Test contains with non-existent product."""
        assert "nonexistent" not in populated_collection

    def test_str_representation(self, populated_collection) -> None:
        """Test string representation."""
        str_repr = str(populated_collection)

        assert "ProductCollection" in str_repr
        assert "products=3" in str_repr

    def test_repr_representation(self, populated_collection) -> None:
        """Test detailed string representation."""
        repr_str = repr(populated_collection)

        assert "ProductCollection" in repr_str
        assert "product1" in repr_str
        assert "product2" in repr_str
        assert "product3" in repr_str

    def test_get_product_folders_valid_directory(self) -> None:
        """Test getting product folders from valid directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_path = Path(temp_dir)

            # Create product folders with description.xml
            (installer_path / "product1").mkdir()
            (installer_path / "product1" / "description.xml").write_text(
                "<product></product>"
            )

            (installer_path / "product2").mkdir()
            (installer_path / "product2" / "description.xml").write_text(
                "<product></product>"
            )

            # Create folder without description.xml
            (installer_path / "invalid").mkdir()

            collection = ProductCollection()
            folders = collection.get_product_folders(str(installer_path))

            assert folders == ["product1", "product2"]

    def test_get_product_folders_invalid_directory(self) -> None:
        """Test getting product folders from invalid directory."""
        collection = ProductCollection()
        folders = collection.get_product_folders("/nonexistent/path")

        assert folders == []

    @patch("kbot_installer.core.product.collection.Product.from_installer_folder")
    def test_load_product_existing(self, mock_from_installer_folder) -> None:
        """Test loading an existing product."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_path = Path(temp_dir)
            product_folder = installer_path / "test_product"
            product_folder.mkdir()

            # Create description.xml
            description_xml = """
            <product>
                <name>test_product</name>
                <version>1.0.0</version>
                <type>solution</type>
            </product>
            """
            (product_folder / "description.xml").write_text(description_xml)

            # Mock Product.from_installer_folder to return a test product
            mock_product = Product(
                name="test_product", version="1.0.0", type="solution"
            )
            mock_from_installer_folder.return_value = mock_product

            collection = ProductCollection()
            product = collection.load_product(str(installer_path), "test_product")

            assert product is not None
            assert product.name == "test_product"
            assert product.version == "1.0.0"
            mock_from_installer_folder.assert_called_once_with(str(product_folder))

    def test_load_product_nonexistent(self) -> None:
        """Test loading a non-existent product."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = ProductCollection()
            product = collection.load_product(temp_dir, "nonexistent")

            assert product is None

    def test_load_product_no_description_xml(self) -> None:
        """Test loading a product without description.xml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_path = Path(temp_dir)
            product_folder = installer_path / "test_product"
            product_folder.mkdir()
            # No description.xml file

            collection = ProductCollection()
            product = collection.load_product(str(installer_path), "test_product")

            assert product is None

    def test_validate_installer_valid(self) -> None:
        """Test validating a valid installer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_path = Path(temp_dir)

            # Create product folder with valid description.xml
            product_folder = installer_path / "test_product"
            product_folder.mkdir()
            description_xml = """
            <product>
                <name>test_product</name>
                <version>1.0.0</version>
                <type>solution</type>
            </product>
            """
            (product_folder / "description.xml").write_text(description_xml)

            collection = ProductCollection()
            is_valid, errors = collection.validate_installer(str(installer_path))

            assert is_valid is True
            assert errors == []

    def test_validate_installer_invalid_directory(self) -> None:
        """Test validating an invalid directory."""
        collection = ProductCollection()
        is_valid, errors = collection.validate_installer("/nonexistent/path")

        assert is_valid is False
        assert "Installer path is not a directory" in errors

    def test_validate_installer_no_products(self) -> None:
        """Test validating an installer with no products."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = ProductCollection()
            is_valid, errors = collection.validate_installer(temp_dir)

            assert is_valid is False
            assert "No product folders found" in errors

    def test_export_to_json(self, populated_collection) -> None:
        """Test exporting collection to JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            file_path = f.name

        try:
            populated_collection.export_to_json(file_path)

            # Verify file was created and contains expected data
            with Path(file_path).open(encoding="utf-8") as f:
                data = json.load(f)

            assert "products" in data
            assert len(data["products"]) == 3

            # Check first product
            product1 = data["products"][0]
            assert product1["name"] == "product1"
            assert product1["version"] == "1.0.0"
            assert product1["type"] == "solution"

        finally:
            Path(file_path).unlink(missing_ok=True)

    def test_export_to_xml(self, populated_collection) -> None:
        """Test exporting collection to XML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            file_path = f.name

        try:
            populated_collection.export_to_xml(file_path)

            # Verify file was created and contains expected data
            from defusedxml import ElementTree

            tree = ElementTree.parse(file_path)
            root = tree.getroot()

            assert root.tag == "products"
            assert len(root) == 3

            # Check first product
            product1 = root[0]
            assert product1.tag == "product"
            assert product1.get("name") == "product1"
            assert product1.get("version") == "1.0.0"
            assert product1.get("type") == "solution"

        finally:
            Path(file_path).unlink(missing_ok=True)

    @patch("kbot_installer.core.product.collection.Product.from_installer_folder")
    def test_from_installer_success(self, mock_from_installer, sample_products) -> None:
        """Test creating collection from installer directory successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_path = Path(temp_dir)

            # Create product folders
            (installer_path / "product1").mkdir()
            (installer_path / "product1" / "description.xml").write_text(
                "<product></product>"
            )

            (installer_path / "product2").mkdir()
            (installer_path / "product2" / "description.xml").write_text(
                "<product></product>"
            )

            # Mock Product.from_installer_folder to return sample products
            mock_from_installer.side_effect = sample_products[:2]

            collection = ProductCollection.from_installer(str(installer_path))

            assert len(collection.products) == 2
            assert collection.products == sample_products[:2]

    def test_from_installer_invalid_directory(self) -> None:
        """Test creating collection from invalid directory."""
        with pytest.raises(NotADirectoryError):
            ProductCollection.from_installer("/nonexistent/path")

    @patch("kbot_installer.core.product.collection.Product.from_installer_folder")
    def test_from_installer_with_failures(self, mock_from_installer) -> None:
        """Test creating collection from installer with product loading failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_path = Path(temp_dir)

            # Create product folders
            (installer_path / "product1").mkdir()
            (installer_path / "product1" / "description.xml").write_text(
                "<product></product>"
            )

            (installer_path / "product2").mkdir()
            (installer_path / "product2" / "description.xml").write_text(
                "<product></product>"
            )

            # Mock Product.from_installer_folder to raise ValueError for one product
            def side_effect(path):
                if "product1" in path:
                    return Product(name="product1", version="1.0.0")
                error_msg = "Invalid product"
                raise ValueError(error_msg)

            mock_from_installer.side_effect = side_effect

            with pytest.raises(ValueError, match="Failed to load products"):
                ProductCollection.from_installer(str(installer_path))

    def test_from_installer_folder_alias(self) -> None:
        """Test that from_installer_folder is an alias for from_installer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installer_path = Path(temp_dir)

            # Create product folder
            (installer_path / "product1").mkdir()
            (installer_path / "product1" / "description.xml").write_text(
                "<product></product>"
            )

            with patch(
                "kbot_installer.core.product.collection.Product.from_installer_folder"
            ) as mock_from_installer:
                mock_from_installer.return_value = Product(
                    name="product1", version="1.0.0"
                )

                ProductCollection.from_installer(str(installer_path))
                ProductCollection.from_installer_folder(str(installer_path))

                # Both should call the same method
                assert mock_from_installer.call_count == 2

    def test_empty_collection_operations(self, empty_collection) -> None:
        """Test operations on empty collection."""
        assert len(empty_collection) == 0
        assert list(empty_collection) == []
        assert empty_collection.get_product_names() == []
        assert empty_collection.get_all_products() == []
        assert empty_collection.get_products_by_type("solution") == []
        assert empty_collection.get_products_by_category("test") == []
        assert empty_collection.filter_products() == []
        assert "nonexistent" not in empty_collection
        assert str(empty_collection) == "ProductCollection(products=0)"
        assert repr(empty_collection) == "ProductCollection(products=[])"

    def test_remove_product_empty_collection(self, empty_collection) -> None:
        """Test removing product from empty collection."""
        result = empty_collection.remove_product("nonexistent")
        assert result is False

    def test_get_product_empty_collection(self, empty_collection) -> None:
        """Test getting product from empty collection."""
        product = empty_collection.get_product("nonexistent")
        assert product is None
