"""ProductCollection class for managing collections of products."""

from __future__ import annotations

import fnmatch
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override

from installable.dependency_graph import DependencyGraph
from installable.factory import create_installable
from installer_support.installer_utils import version_to_branch

if TYPE_CHECKING:
    from installable.product_installable import ProductInstallable


class ProductCollection(BaseModel):
    """Manages a collection of products."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    products: Annotated[list[ProductInstallable], Field(default_factory=list)]

    def __init__(
        self,
        products: list[ProductInstallable] | None = None,
        **data: Any,
    ) -> None:
        """Initialize collection, accepting a legacy positional products list."""
        if products is not None:
            data["products"] = products
        super().__init__(**data)

    def add_product(self, product: ProductInstallable) -> None:
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
            if product.product.name == product_name:
                del self.products[i]
                return True
        return False

    def get_product(self, name: str) -> ProductInstallable | None:
        """Get a product by name.

        Args:
            name: Product name.

        Returns:
            Product instance or None if not found.

        """
        for product in self.products:
            if product.product.name == name:
                return product
        return None

    def get_all_products(self) -> list[ProductInstallable]:
        """Get all products in the collection.

        Returns:
            List of all products.

        """
        return self.products.copy()

    def get_products_by_type(self, product_type: str) -> list[ProductInstallable]:
        """Get products filtered by type.

        Args:
            product_type: Type to filter by.

        Returns:
            List of products of the specified type.

        """
        return [p for p in self.products if p.product.type == product_type]

    def get_products_by_category(self, category: str) -> list[ProductInstallable]:
        """Get products filtered by category.

        Args:
            category: Category to filter by.

        Returns:
            List of products containing the specified category.

        """
        return [p for p in self.products if category in p.product.category_names]

    def get_product_names(self) -> list[str]:
        """Get list of all product names.

        Returns:
            List of product names.

        """
        return [p.product.name for p in self.products]

    def filter_products(self, **filters: str) -> list[ProductInstallable]:
        """Filter products by various criteria.

        Args:
            **filters: Filter criteria (type, category, etc.).

        Returns:
            List of filtered products.

        """
        filtered = self.products

        if "type" in filters:
            filtered = [p for p in filtered if p.product.type == filters["type"]]

        if "category" in filters:
            filtered = [
                p for p in filtered if filters["category"] in p.product.category_names
            ]

        if "has_parents" in filters:
            if filters["has_parents"]:
                filtered = [p for p in filtered if p.product.parent_names]
            else:
                filtered = [p for p in filtered if not p.product.parent_names]

        return filtered

    @classmethod
    def from_installer(cls, installer_path: str) -> ProductCollection:
        """Create collection from installer directory.

        Args:
            installer_path: Path to installer directory.

        Returns:
            ProductCollection instance.

        Raises:
            ValueError: If installer is invalid.

        """
        resolved_path = Path(installer_path).resolve()
        if not resolved_path.is_dir():
            msg = f"Installer path is not a directory: {resolved_path}"
            raise NotADirectoryError(msg)

        products = []
        failed_products = []

        # Find product folders
        product_folders = sorted(
            item.name
            for item in resolved_path.iterdir()
            if item.is_dir() and (item / "description.xml").exists()
        )

        for product_name in product_folders:
            try:
                product = cast(
                    "ProductInstallable",
                    create_installable("product", name=product_name),
                )
                product.load_from_installer_folder(resolved_path / product_name)
                products.append(product)
            except (ValueError, FileNotFoundError) as e:
                failed_products.append(f"{product_name}: {e}")

        if failed_products:
            msg = f"Failed to load products: {'; '.join(failed_products)}"
            raise ValueError(msg)

        return cls(products)

    @classmethod
    def from_installer_folder(cls, installer_path: str) -> ProductCollection:
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
        resolved_path = Path(installer_path).resolve()
        if not resolved_path.is_dir():
            return []

        return sorted(
            item.name
            for item in resolved_path.iterdir()
            if item.is_dir() and (item / "description.xml").exists()
        )

    def load_product(
        self, installer_path: str, product_name: str
    ) -> ProductInstallable | None:
        """Load a specific product from installer directory.

        Args:
            installer_path: Path to installer directory.
            product_name: Name of the product folder.

        Returns:
            Product instance or None if not found.

        """
        resolved_path = Path(installer_path).resolve()
        product_folder = resolved_path / product_name

        if (
            not product_folder.exists()
            or not (product_folder / "description.xml").exists()
        ):
            return None

        try:
            product = cast(
                "ProductInstallable",
                create_installable("product", name=product_name),
            )
            product.load_from_installer_folder(product_folder)
        except (ValueError, FileNotFoundError):
            return None
        else:
            return product

    def validate_installer(self, installer_path: str) -> tuple[bool, list[str]]:
        """Validate the installer structure.

        Args:
            installer_path: Path to installer directory.

        Returns:
            Tuple of (is_valid, error_messages).

        """
        resolved_path = Path(installer_path).resolve()
        if not resolved_path.is_dir():
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

    def clone_with_dependencies(self, root_product_name: str, base_path: Path) -> None:
        """Clone a product and all its dependencies using BFS order.

        Args:
            root_product_name: Name of the root product to clone.
            base_path: Base path for cloning.

        """
        graph = DependencyGraph(self.products)
        bfs_products = graph.get_bfs_ordered_products(root_product_name)

        for product in bfs_products:
            product_path = base_path / product.product.name
            branch = product.branch
            if not branch and product.product.version:
                branch = version_to_branch(
                    product.product.version.to_str(), env=product.env
                )
            product.provider.clone_and_checkout(
                product_path, branch, repository_name=product.product.name
            )
            product.load_from_installer_folder(product_path)

    @override
    def __iter__(self) -> Iterator[ProductInstallable]:
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

    @override
    def __str__(self) -> str:
        """Return string representation of ProductCollection."""
        return f"ProductCollection(products={len(self.products)})"

    def get_files(
        self, relpath: str, pattern: str, *, exts: tuple[str, ...] | None = None
    ) -> list[Path]:
        """Get files matching pattern in relative path across all products.

        This method searches for files in the relative path within each product's
        directory, similar to the old ProductList.get_files() method.

        Args:
            relpath: Relative path from product directory (e.g., 'core/python').
            pattern: File pattern to match (e.g., '*' or 'description.xml').
            exts: Optional tuple of file extensions to filter (e.g., ('.py', '.so')).

        Returns:
            List of Path objects matching the pattern, sorted by product order.

        """
        files: list[Path] = []

        for product in self.products:
            if not product.dirname:
                continue

            search_path = product.dirname / relpath
            if not search_path.exists():
                continue

            if search_path.is_file():
                files.extend(self._get_files_from_path(search_path, pattern, exts))
            elif search_path.is_dir():
                files.extend(self._get_files_from_directory(search_path, pattern, exts))

        return files

    def _get_files_from_path(
        self, path: Path, pattern: str, exts: tuple[str, ...] | None
    ) -> list[Path]:
        """Get files from a single path matching pattern and extensions."""
        if not fnmatch.fnmatch(path.name, pattern):
            return []

        if exts and path.suffix not in exts:
            return []

        return [path]

    def _get_files_from_directory(
        self, directory: Path, pattern: str, exts: tuple[str, ...] | None
    ) -> list[Path]:
        """Get files from directory recursively matching pattern and extensions."""
        return [
            file_path
            for file_path in directory.rglob(pattern)
            if file_path.is_file() and (exts is None or file_path.suffix in exts)
        ]

    @override
    def __repr__(self) -> str:
        """Detailed string representation of ProductCollection."""
        return f"ProductCollection(products={[p.product.name for p in self.products]})"
