"""ProductCollection class for managing collections of products."""

import json
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET

from kbot_installer.core.product.product import Product


class ProductCollection:
    """Manages a collection of products.

    Attributes:
        products: List of Product instances.

    """

    def __init__(self, products: list[Product] | None = None) -> None:
        """Initialize collection with products.

        Args:
            products: List of Product instances.

        """
        self.products = products or []

    def add_product(self, product: Product) -> None:
        """Add a product to the collection.

        Args:
            product: Product to add.

        """
        self.products.append(product)

    def remove_product(self, product_name: str) -> bool:
        """Remove a product from the collection.

        Args:
            product_name: Name of product to remove.

        Returns:
            True if product was removed, False if not found.

        """
        for i, product in enumerate(self.products):
            if product.name == product_name:
                del self.products[i]
                return True
        return False

    def get_product(self, name: str) -> Product | None:
        """Get a product by name.

        Args:
            name: Product name.

        Returns:
            Product instance or None if not found.

        """
        for product in self.products:
            if product.name == name:
                return product
        return None

    def get_all_products(self) -> list[Product]:
        """Get all products in the collection.

        Returns:
            List of all products.

        """
        return self.products.copy()

    def get_products_by_type(self, product_type: str) -> list[Product]:
        """Get products filtered by type.

        Args:
            product_type: Type to filter by.

        Returns:
            List of products of the specified type.

        """
        return [p for p in self.products if p.type == product_type]

    def get_products_by_category(self, category: str) -> list[Product]:
        """Get products filtered by category.

        Args:
            category: Category to filter by.

        Returns:
            List of products containing the specified category.

        """
        return [p for p in self.products if category in p.categories]

    def get_product_names(self) -> list[str]:
        """Get list of all product names.

        Returns:
            List of product names.

        """
        return [p.name for p in self.products]

    def filter_products(self, **filters: str) -> list[Product]:
        """Filter products by various criteria.

        Args:
            **filters: Filter criteria (type, category, etc.).

        Returns:
            List of filtered products.

        """
        filtered = self.products

        if "type" in filters:
            filtered = [p for p in filtered if p.type == filters["type"]]

        if "category" in filters:
            filtered = [p for p in filtered if filters["category"] in p.categories]

        if "has_parents" in filters:
            if filters["has_parents"]:
                filtered = [p for p in filtered if p.parents]
            else:
                filtered = [p for p in filtered if not p.parents]

        return filtered

    @classmethod
    def from_installer(cls, installer_path: str) -> "ProductCollection":
        """Create collection from installer directory.

        Args:
            installer_path: Path to installer directory.

        Returns:
            ProductCollection instance.

        Raises:
            ValueError: If installer is invalid.

        """
        installer_path = Path(installer_path).resolve()
        if not installer_path.is_dir():
            msg = f"Installer path is not a directory: {installer_path}"
            raise NotADirectoryError(msg)

        products = []
        failed_products = []

        # Find product folders
        product_folders = sorted(
            item.name
            for item in installer_path.iterdir()
            if item.is_dir() and (item / "description.xml").exists()
        )

        for product_name in product_folders:
            try:
                product = Product.from_installer_folder(
                    str(installer_path / product_name)
                )
                if product:
                    products.append(product)
            except ValueError as e:
                failed_products.append(f"{product_name}: {e}")

        if failed_products:
            msg = f"Failed to load products: {'; '.join(failed_products)}"
            raise ValueError(msg)

        return cls(products)

    @classmethod
    def from_installer_folder(cls, installer_path: str) -> "ProductCollection":
        """Create collection from installer directory (alias for from_installer).

        Args:
            installer_path: Path to installer directory.

        Returns:
            ProductCollection instance.

        """
        return cls.from_installer(installer_path)

    def get_product_folders(self, installer_path: str) -> list[str]:
        """Get list of product folder names from installer directory.

        Args:
            installer_path: Path to installer directory.

        Returns:
            List of product folder names.

        """
        installer_path = Path(installer_path).resolve()
        if not installer_path.is_dir():
            return []

        return sorted(
            item.name
            for item in installer_path.iterdir()
            if item.is_dir() and (item / "description.xml").exists()
        )

    def load_product(self, installer_path: str, product_name: str) -> Product | None:
        """Load a specific product from installer directory.

        Args:
            installer_path: Path to installer directory.
            product_name: Name of the product folder.

        Returns:
            Product instance or None if not found.

        """
        installer_path = Path(installer_path).resolve()
        product_folder = installer_path / product_name

        if (
            not product_folder.exists()
            or not (product_folder / "description.xml").exists()
        ):
            return None

        try:
            return Product.from_installer_folder(str(product_folder))
        except ValueError:
            return None

    def validate_installer(self, installer_path: str) -> tuple[bool, list[str]]:
        """Validate the installer structure.

        Args:
            installer_path: Path to installer directory.

        Returns:
            Tuple of (is_valid, error_messages).

        """
        installer_path = Path(installer_path).resolve()
        if not installer_path.is_dir():
            return False, ["Installer path is not a directory"]

        errors = []
        product_folders = self.get_product_folders(str(installer_path))

        if not product_folders:
            errors.append("No product folders found")

        for product_name in product_folders:
            try:
                self.load_product(str(installer_path), product_name)
            except ValueError as e:
                errors.append(f"Invalid product '{product_name}': {e}")

        return len(errors) == 0, errors

    def export_to_json(self, file_path: str) -> None:
        """Export collection to JSON file.

        Args:
            file_path: Path to output JSON file.

        """
        data = {
            "products": [
                {
                    "name": p.name,
                    "version": p.version,
                    "type": p.type,
                    "parents": p.parents,
                    "categories": p.categories,
                    "build": p.build,
                    "date": p.date,
                    "license": p.license,
                    "display": p.display,
                    "build_details": p.build_details,
                }
                for p in self.products
            ]
        }

        Path(file_path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def export_to_xml(self, file_path: str) -> None:
        """Export collection to XML file.

        Args:
            file_path: Path to output XML file.

        """
        root = ET.Element("products")
        for product in self.products:
            product_elem = ET.SubElement(root, "product")
            product_elem.set("name", product.name)
            product_elem.set("version", product.version)
            product_elem.set("type", product.type)
            if product.build:
                product_elem.set("build", product.build)
            if product.date:
                product_elem.set("date", product.date)

            if product.parents:
                parents_elem = ET.SubElement(product_elem, "parents")
                for parent in product.parents:
                    parent_elem = ET.SubElement(parents_elem, "parent")
                    parent_elem.set("name", parent)

            if product.categories:
                categories_elem = ET.SubElement(product_elem, "categories")
                for category in product.categories:
                    category_elem = ET.SubElement(categories_elem, "category")
                    category_elem.set("name", category)

        tree = ET.ElementTree(root)
        tree.write(file_path, encoding="utf-8", xml_declaration=True)

    def clone_with_dependencies(self, root_product_name: str, base_path: Path) -> None:
        """Clone a product and all its dependencies using BFS order.

        Args:
            root_product_name: Name of the root product to clone.
            base_path: Base path for cloning.

        """
        from kbot_installer.core.product.dependency_graph import DependencyGraph

        graph = DependencyGraph(self.products)
        bfs_products = graph.get_bfs_ordered_products(root_product_name)

        for product in bfs_products:
            product_path = base_path / product.name
            product.provider.clone_and_checkout(product_path, product.version)
            product.load_from_installer_folder(product_path)

    def to_bfs_ordered_dict(self, root_product_name: str) -> dict[str, str]:
        """Convert collection to BFS-ordered dictionary.

        Args:
            root_product_name: Starting product name.

        Returns:
            Dictionary with product.name: product.to_json() in BFS order.

        """
        from kbot_installer.core.product.dependency_graph import DependencyGraph

        graph = DependencyGraph(self.products)
        bfs_products = graph.get_bfs_ordered_products(root_product_name)

        return {product.name: product.to_json() for product in bfs_products}

    def save_bfs_ordered_json(self, file_path: Path, root_product_name: str) -> None:
        """Save collection as BFS-ordered JSON.

        Args:
            file_path: Path to save the JSON file.
            root_product_name: Starting product name.

        """
        bfs_dict = self.to_bfs_ordered_dict(root_product_name)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(bfs_dict, f, indent=2, ensure_ascii=False)

    def __iter__(self) -> Iterator[Product]:
        """Iterate over products in the collection.

        Yields:
            Product instances.

        """
        yield from self.products

    def __len__(self) -> int:
        """Get number of products in collection.

        Returns:
            Number of products.

        """
        return len(self.products)

    def __contains__(self, product_name: str) -> bool:
        """Check if product exists in collection.

        Args:
            product_name: Name of product to check.

        Returns:
            True if product exists.

        """
        return self.get_product(product_name) is not None

    def __str__(self) -> str:
        """Return string representation of ProductCollection."""
        return f"ProductCollection(products={len(self.products)})"

    def __repr__(self) -> str:
        """Detailed string representation of ProductCollection."""
        return f"ProductCollection(products={[p.name for p in self.products]})"
