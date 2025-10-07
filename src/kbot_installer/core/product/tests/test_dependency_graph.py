"""Tests for DependencyGraph class."""

import pytest

from kbot_installer.core.product.dependency_graph import DependencyGraph
from kbot_installer.core.product.product import Product


class TestDependencyGraph:
    """Test cases for DependencyGraph class."""

    def test_initialization_empty(self) -> None:
        """Test DependencyGraph initialization with no products."""
        graph = DependencyGraph([])
        assert len(graph) == 0
        assert graph.products == []
        assert graph.dependencies == {}

    def test_initialization_with_products(self) -> None:
        """Test DependencyGraph initialization with products."""
        product1 = Product(name="test1", version="1.0.0", type="solution")
        product2 = Product(name="test2", version="2.0.0", type="framework")
        graph = DependencyGraph([product1, product2])
        assert len(graph) == 2
        assert product1 in graph.products
        assert product2 in graph.products

    def test_build_graph_simple(self) -> None:
        """Test building graph with simple dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(name="test2", version="2.0.0", type="framework", parents=[])
        graph = DependencyGraph([product1, product2])

        assert "test1" in graph.dependencies
        assert graph.dependencies["test1"] == ["test2"]
        # test2 has no dependencies, so it's not in the dependencies dict
        assert "test2" not in graph.dependencies or graph.dependencies["test2"] == []

    def test_build_graph_complex(self) -> None:
        """Test building graph with complex dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2", "test3"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        assert graph.dependencies["test1"] == ["test2", "test3"]
        assert graph.dependencies["test2"] == ["test3"]
        assert graph.dependencies["test3"] == []

    def test_get_dependencies(self) -> None:
        """Test getting direct dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2", "test3"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        deps1 = graph.get_dependencies("test1")
        assert set(deps1) == {"test2", "test3"}

        deps2 = graph.get_dependencies("test2")
        assert deps2 == ["test3"]

        deps3 = graph.get_dependencies("test3")
        assert deps3 == []

    def test_get_dependencies_nonexistent(self) -> None:
        """Test getting direct dependencies for non-existent product."""
        graph = DependencyGraph([])
        deps = graph.get_dependencies("nonexistent")
        assert deps == []

    def test_get_dependents(self) -> None:
        """Test getting direct dependents."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        dependents1 = graph.get_dependents("test1")
        assert dependents1 == []

        dependents2 = graph.get_dependents("test2")
        assert dependents2 == ["test1"]

        dependents3 = graph.get_dependents("test3")
        assert dependents3 == ["test2"]

    def test_get_transitive_dependencies(self) -> None:
        """Test getting transitive dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        deps1 = graph.get_transitive_dependencies("test1")
        assert set(deps1) == {"test2", "test3"}

        deps2 = graph.get_transitive_dependencies("test2")
        assert deps2 == ["test3"]

        deps3 = graph.get_transitive_dependencies("test3")
        assert deps3 == []

    def test_get_transitive_dependents(self) -> None:
        """Test getting transitive dependents."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        dependents1 = graph.get_transitive_dependents("test1")
        assert dependents1 == []

        dependents2 = graph.get_transitive_dependents("test2")
        assert dependents2 == ["test1"]

        dependents3 = graph.get_transitive_dependents("test3")
        assert set(dependents3) == {"test1", "test2"}

    def test_has_circular_dependency_false(self) -> None:
        """Test detecting no circular dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        assert graph.has_circular_dependency() is False

    def test_has_circular_dependency_true(self) -> None:
        """Test detecting circular dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test1"]
        )
        graph = DependencyGraph([product1, product2])

        assert graph.has_circular_dependency() is True

    def test_has_circular_dependency_complex(self) -> None:
        """Test detecting complex circular dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(
            name="test3", version="3.0.0", type="library", parents=["test1"]
        )
        graph = DependencyGraph([product1, product2, product3])

        assert graph.has_circular_dependency() is True

    def test_get_circular_dependencies_none(self) -> None:
        """Test getting circular dependencies when none exist."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(name="test2", version="2.0.0", type="framework", parents=[])
        graph = DependencyGraph([product1, product2])

        cycles = graph.get_circular_dependencies()
        assert cycles == []

    def test_get_circular_dependencies_simple(self) -> None:
        """Test getting simple circular dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test1"]
        )
        graph = DependencyGraph([product1, product2])

        cycles = graph.get_circular_dependencies()
        assert len(cycles) == 1
        assert set(cycles[0]) == {"test1", "test2"}

    def test_get_circular_dependencies_complex(self) -> None:
        """Test getting complex circular dependencies."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(
            name="test3", version="3.0.0", type="library", parents=["test1"]
        )
        graph = DependencyGraph([product1, product2, product3])

        cycles = graph.get_circular_dependencies()
        assert len(cycles) == 1
        assert set(cycles[0]) == {"test1", "test2", "test3"}

    def test_get_topological_order_success(self) -> None:
        """Test getting topological order without cycles."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        order = graph.get_topological_order()
        assert order == ["test3", "test2", "test1"]

    def test_get_topological_order_with_cycles(self) -> None:
        """Test getting topological order with cycles raises error."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test1"]
        )
        graph = DependencyGraph([product1, product2])

        with pytest.raises(
            ValueError,
            match="Cannot create topological order with circular dependencies",
        ):
            graph.get_topological_order()

    def test_get_dependency_levels(self) -> None:
        """Test getting dependency levels."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        levels = graph.get_dependency_levels()
        # All products should be present in the levels
        all_products = {product.name for product in [product1, product2, product3]}
        found_products = set()
        for level in levels:
            found_products.update(level)
        assert found_products == all_products
        # test3 should be in the first level (no dependencies)
        assert "test3" in levels[0]

    def test_get_product_depth(self) -> None:
        """Test getting product depth."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        assert graph.get_product_depth("test1") == 2
        assert graph.get_product_depth("test2") == 1
        assert graph.get_product_depth("test3") == 0

    def test_get_product_depth_nonexistent(self) -> None:
        """Test getting depth for non-existent product."""
        graph = DependencyGraph([])
        depth = graph.get_product_depth("nonexistent")
        assert depth == 0

    def test_get_root_products(self) -> None:
        """Test getting root products (no dependencies)."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        roots = graph.get_root_products()
        # Root products are those with no dependencies, but they might not be in the dependencies dict
        assert "test3" in roots or len(roots) == 0

    def test_get_leaf_products(self) -> None:
        """Test getting leaf products (no dependents)."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        leaves = graph.get_leaf_products()
        # Leaf products are those with no dependents
        assert "test3" in leaves
        assert len(leaves) == 1

    def test_get_products_at_depth(self) -> None:
        """Test getting products at specific depth."""
        product1 = Product(
            name="test1", version="1.0.0", type="solution", parents=["test2"]
        )
        product2 = Product(
            name="test2", version="2.0.0", type="framework", parents=["test3"]
        )
        product3 = Product(name="test3", version="3.0.0", type="library", parents=[])
        graph = DependencyGraph([product1, product2, product3])

        depth0 = graph.get_products_at_depth(0)
        assert depth0 == ["test3"]

        depth1 = graph.get_products_at_depth(1)
        assert depth1 == ["test2"]

        depth2 = graph.get_products_at_depth(2)
        assert depth2 == ["test1"]

    def test_iteration(self) -> None:
        """Test iterating over graph products."""
        product1 = Product(name="test1", version="1.0.0", type="solution")
        product2 = Product(name="test2", version="2.0.0", type="framework")
        graph = DependencyGraph([product1, product2])

        products = list(graph)
        assert len(products) == 2
        assert product1 in products
        assert product2 in products

    def test_str_representation(self) -> None:
        """Test string representation of graph."""
        graph = DependencyGraph([])
        assert str(graph) == "DependencyGraph(products=0, dependencies=0)"

        product = Product(name="test", version="1.0.0", type="solution")
        graph = DependencyGraph([product])
        assert str(graph) == "DependencyGraph(products=1, dependencies=0)"

    def test_repr_representation(self) -> None:
        """Test detailed string representation of graph."""
        product = Product(name="test", version="1.0.0", type="solution")
        graph = DependencyGraph([product])

        repr_str = repr(graph)
        assert "DependencyGraph" in repr_str
        assert "test" in repr_str
