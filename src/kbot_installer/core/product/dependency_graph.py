"""DependencyGraph class for managing product dependencies."""

from collections import defaultdict, deque
from collections.abc import Iterator

from kbot_installer.core.product.installable_base import InstallableBase


class DependencyGraph:
    """Manages product dependency relationships and analysis.

    Attributes:
        products: List of Product instances.
        dependencies: Dictionary mapping product names to their dependencies.
        dependents: Dictionary mapping product names to products that depend on them.

    """

    def __init__(self, products: list[InstallableBase]) -> None:
        """Initialize dependency graph with products.

        Args:
            products: List of Product instances.

        """
        self.products = products
        self.dependencies = defaultdict(list)
        self.dependents = defaultdict(list)
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the dependency graph from products."""
        # Build dependency relationships

        for product in self.products:
            for parent_name in product.parents:
                # Add dependency
                self.dependencies[product.name].append(parent_name)
                # Add dependent relationship
                self.dependents[parent_name].append(product.name)

    def get_dependencies(self, product_name: str) -> list[str]:
        """Get direct dependencies of a product.

        Args:
            product_name: Name of the product.

        Returns:
            List of direct dependency names.

        """
        return self.dependencies[product_name].copy()

    def get_dependents(self, product_name: str) -> list[str]:
        """Get products that depend on the given product.

        Args:
            product_name: Name of the product.

        Returns:
            List of dependent product names.

        """
        return self.dependents[product_name].copy()

    def get_transitive_dependencies(self, product_name: str) -> list[str]:
        """Get all transitive dependencies of a product.

        Args:
            product_name: Name of the product.

        Returns:
            List of all transitive dependency names.

        """
        visited = set()
        dependencies = []
        stack = [product_name]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for dep in self.dependencies[current]:
                if dep not in visited:
                    dependencies.append(dep)
                    stack.append(dep)

        return dependencies

    def get_transitive_dependents(self, product_name: str) -> list[str]:
        """Get all products that transitively depend on the given product.

        Args:
            product_name: Name of the product.

        Returns:
            List of all transitive dependent names.

        """
        visited = set()
        dependents = []
        stack = [product_name]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            for dep in self.dependents[current]:
                if dep not in visited:
                    dependents.append(dep)
                    stack.append(dep)

        return dependents

    def has_circular_dependency(self) -> bool:
        """Check if there are any circular dependencies.

        Returns:
            True if circular dependencies exist.

        """
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.dependencies[node]:
                if has_cycle(neighbor):
                    return True

            rec_stack.remove(node)
            return False

        for product in self.products:
            if product.name not in visited and has_cycle(product.name):
                return True

        return False

    def get_circular_dependencies(self) -> list[list[str]]:
        """Get all circular dependency chains.

        Returns:
            List of circular dependency chains.

        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def find_cycles(node: str) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append([*path[cycle_start:], node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.dependencies[node]:
                find_cycles(neighbor)

            path.pop()
            rec_stack.remove(node)

        for product in self.products:
            if product.name not in visited:
                find_cycles(product.name)

        return cycles

    def get_topological_order(self) -> list[str]:
        """Get products in topological order (dependencies first).

        Returns:
            List of product names in topological order.

        Raises:
            ValueError: If circular dependencies exist.

        """
        if self.has_circular_dependency():
            msg = "Cannot create topological order with circular dependencies"
            raise ValueError(msg)

        # Kahn's algorithm
        in_degree = defaultdict(int)
        for product in self.products:
            in_degree[product.name] = len(self.dependencies[product.name])

        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            for dependent in self.dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def get_leaf_products(self) -> list[str]:
        """Get products with no dependencies.

        Returns:
            List of leaf product names.

        """
        # Get all product names
        all_products = {product.name for product in self.products}
        # Find products that have no dependencies
        return [name for name in all_products if not self.dependencies.get(name, [])]

    def get_root_products(self) -> list[str]:
        """Get products that no other products depend on.

        Returns:
            List of root product names.

        """
        return [name for name, deps in self.dependents.items() if not deps]

    def get_dependency_levels(self) -> list[list[str]]:
        """Get products organized by dependency levels.

        Returns:
            List of lists, where each inner list contains products at the same level.

        """
        levels = []
        remaining = {p.name for p in self.products}
        processed = set()

        while remaining:
            current_level = []
            for product_name in list(remaining):
                # Check if all dependencies are processed
                deps = set(self.dependencies[product_name])
                if deps.issubset(processed):
                    current_level.append(product_name)
                    remaining.remove(product_name)
                    processed.add(product_name)

            if not current_level:
                # Circular dependency or error
                break

            levels.append(current_level)

        return levels

    def get_bfs_order(self, root_product_name: str) -> list[str]:
        """Get products in BFS order starting from root.

        Args:
            root_product_name: Starting product name.

        Returns:
            List of product names in BFS order.

        """
        queue = deque([root_product_name])
        processed = set()
        result = []

        while queue:
            current = queue.popleft()

            if current in processed:
                continue

            result.append(current)
            processed.add(current)

            # Add dependencies to queue
            for dep in self.dependencies[current]:
                if dep not in processed:
                    queue.append(dep)

        return result

    def get_bfs_ordered_products(self, root_product_name: str) -> list[InstallableBase]:
        """Get Product instances in BFS order.

        Args:
            root_product_name: Starting product name.

        Returns:
            List of Product instances in BFS order.

        """
        product_map = {p.name: p for p in self.products}
        bfs_names = self.get_bfs_order(root_product_name)
        return [product_map[name] for name in bfs_names if name in product_map]

    def get_product_depth(self, product_name: str) -> int:
        """Get the maximum depth of dependencies for a product.

        Args:
            product_name: Name of the product.

        Returns:
            Maximum dependency depth.

        """

        def get_depth(node: str, visited: set) -> int:
            if node in visited:
                return 0  # Circular dependency

            visited.add(node)
            max_depth = 0
            for dep in self.dependencies[node]:
                depth = get_depth(dep, visited.copy())
                max_depth = max(max_depth, depth + 1)

            return max_depth

        return get_depth(product_name, set())

    def get_products_at_depth(self, depth: int) -> list[str]:
        """Get products at a specific dependency depth.

        Args:
            depth: Dependency depth.

        Returns:
            List of product names at the specified depth.

        """
        return [
            product.name
            for product in self.products
            if self.get_product_depth(product.name) == depth
        ]

    def __iter__(self) -> Iterator[InstallableBase]:
        """Iterate over products in the graph.

        Yields:
            Product instances.

        """
        yield from self.products

    def __len__(self) -> int:
        """Get number of products in the graph.

        Returns:
            Number of products.

        """
        return len(self.products)

    def __str__(self) -> str:
        """Return string representation of DependencyGraph."""
        return f"DependencyGraph(products={len(self.products)}, dependencies={len(self.dependencies)})"

    def __repr__(self) -> str:
        """Detailed string representation of DependencyGraph."""
        return f"DependencyGraph(products={[p.name for p in self.products]})"
