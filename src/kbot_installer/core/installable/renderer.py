"""DependencyTreeRenderer class for visualizing dependency trees."""

from kbot_installer.core.installable.dependency_graph import DependencyGraph


class DependencyTreeRenderer:
    """Renders dependency trees in various formats.

    Supports multiple rendering styles:
    - UV tree style (like `uv tree`)
    - File tree style (like directory structure)
    - Custom tree styles
    """

    def __init__(self) -> None:
        """Initialize the renderer."""
        self._visited = set()

    def render_uv_tree_style(self, graph: DependencyGraph) -> str:
        """Render dependency tree in UV tree style.

        Args:
            graph: DependencyGraph to render.

        Returns:
            Formatted tree string.

        """
        lines = []
        self._visited.clear()

        # Find root products (no dependencies)
        root_products = graph.get_root_products()
        if not root_products:
            # If no clear roots, use all products
            all_products = {product.name for product in graph.products}
            root_products = sorted(all_products)

        for root in sorted(root_products):
            self._visited.clear()  # Reset visited for each root
            self._render_uv_node(graph, root, "", "", lines)

        return "\n".join(lines)

    def render_file_tree_style(self, graph: DependencyGraph) -> str:
        """Render dependency tree in file tree style.

        Args:
            graph: DependencyGraph to render.

        Returns:
            Formatted tree string.

        """
        lines = []
        self._visited.clear()

        # Find root products
        root_products = graph.get_root_products()
        if not root_products:
            root_products = graph.get_leaf_products()

        for root in sorted(root_products):
            self._render_file_node(graph, root, "", "", lines)

        return "\n".join(lines)

    def render_tree(self, graph: DependencyGraph, root: str | None = None) -> str:
        """Render dependency tree starting from a specific root.

        Args:
            graph: DependencyGraph to render.
            root: Root product name. If None, uses all root products.

        Returns:
            Formatted tree string.

        """
        lines = []
        self._visited.clear()

        if root:
            if root not in [p.name for p in graph.products]:
                return f"Product '{root}' not found in graph"
            self._render_uv_node(graph, root, "", "", lines)
        else:
            root_products = graph.get_root_products()
            if not root_products:
                root_products = graph.get_leaf_products()

            for root_product in sorted(root_products):
                self._render_uv_node(graph, root_product, "", "", lines)

        return "\n".join(lines)

    def render_dependency_levels(self, graph: DependencyGraph) -> str:
        """Render products organized by dependency levels.

        Args:
            graph: DependencyGraph to render.

        Returns:
            Formatted levels string.

        """
        levels = graph.get_dependency_levels()
        lines = []

        for i, level in enumerate(levels):
            lines.append(f"Level {i}: {', '.join(sorted(level))}")

        return "\n".join(lines)

    def render_topological_order(self, graph: DependencyGraph) -> str:
        """Render products in topological order.

        Args:
            graph: DependencyGraph to render.

        Returns:
            Formatted order string.

        """
        try:
            order = graph.get_topological_order()
            lines = ["Topological order (installation order):"]
            for i, product in enumerate(order, 1):
                lines.append(f"{i:2d}. {product}")
            return "\n".join(lines)
        except ValueError as e:
            return f"Cannot create topological order: {e}"

    def _render_uv_node(
        self,
        graph: DependencyGraph,
        product_name: str,
        prefix: str,
        connector: str,
        lines: list[str],
    ) -> None:
        """Render a single node in UV tree style.

        Args:
            graph: DependencyGraph to render.
            product_name: Name of the product to render.
            prefix: Prefix for the current line.
            connector: Connector character for the current line.
            lines: List to append lines to.

        """
        if product_name in self._visited:
            lines.append(f"{prefix}{connector}{product_name} (circular)")
            return

        self._visited.add(product_name)
        lines.append(f"{prefix}{connector}{product_name}")

        # Get dependencies
        dependencies = sorted(graph.get_dependencies(product_name))
        if not dependencies:
            return

        # Render dependencies
        for i, dep in enumerate(dependencies):
            is_last = i == len(dependencies) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            new_connector = "└── " if is_last else "├── "

            self._render_uv_node(graph, dep, new_prefix, new_connector, lines)

    def _render_file_node(
        self,
        graph: DependencyGraph,
        product_name: str,
        prefix: str,
        connector: str,
        lines: list[str],
    ) -> None:
        """Render a single node in file tree style.

        Args:
            graph: DependencyGraph to render.
            product_name: Name of the product to render.
            prefix: Prefix for the current line.
            connector: Connector character for the current line.
            lines: List to append lines to.

        """
        if product_name in self._visited:
            lines.append(f"{prefix}{connector}{product_name}/ (circular)")
            return

        self._visited.add(product_name)
        lines.append(f"{prefix}{connector}{product_name}/")

        # Get dependencies
        dependencies = sorted(graph.get_dependencies(product_name))
        if not dependencies:
            return

        # Render dependencies
        for i, dep in enumerate(dependencies):
            is_last = i == len(dependencies) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            new_connector = "└── " if is_last else "├── "

            self._render_file_node(graph, dep, new_prefix, new_connector, lines)

    def render_circular_dependencies(self, graph: DependencyGraph) -> str:
        """Render circular dependencies if they exist.

        Args:
            graph: DependencyGraph to render.

        Returns:
            Formatted circular dependencies string.

        """
        cycles = graph.get_circular_dependencies()
        if not cycles:
            return "No circular dependencies found."

        lines = ["Circular dependencies found:"]
        for i, cycle in enumerate(cycles, 1):
            cycle_str = " → ".join(cycle)
            lines.append(f"{i}. {cycle_str}")

        return "\n".join(lines)

    def render_dependency_summary(self, graph: DependencyGraph) -> str:
        """Render a summary of the dependency graph.

        Args:
            graph: DependencyGraph to render.

        Returns:
            Formatted summary string.

        """
        lines = [
            "Dependency Graph Summary:",
            f"Total products: {len(graph)}",
            f"Root products: {len(graph.get_root_products())}",
            f"Leaf products: {len(graph.get_leaf_products())}",
            f"Circular dependencies: {'Yes' if graph.has_circular_dependency() else 'No'}",
        ]

        # Add root products
        root_products = graph.get_root_products()
        if root_products:
            lines.append(f"Root products: {', '.join(sorted(root_products))}")

        # Add leaf products
        leaf_products = graph.get_leaf_products()
        if leaf_products:
            lines.append(f"Leaf products: {', '.join(sorted(leaf_products))}")

        return "\n".join(lines)

    def render_product_info(self, graph: DependencyGraph, product_name: str) -> str:
        """Render detailed information about a specific product.

        Args:
            graph: DependencyGraph to render.
            product_name: Name of the product.

        Returns:
            Formatted product info string.

        """
        # Find the product
        product = None
        for p in graph.products:
            if p.name == product_name:
                product = p
                break

        if not product:
            return f"Product '{product_name}' not found."

        lines = [
            f"Product: {product.name}",
            f"Version: {product.version}",
            f"Type: {product.type}",
            f"Categories: {', '.join(product.categories) if product.categories else 'None'}",
            f"Direct dependencies: {len(graph.get_dependencies(product_name))}",
            f"Direct dependents: {len(graph.get_dependents(product_name))}",
            f"Transitive dependencies: {len(graph.get_transitive_dependencies(product_name))}",
            f"Dependency depth: {graph.get_product_depth(product_name)}",
        ]

        # Add dependencies
        deps = graph.get_dependencies(product_name)
        if deps:
            lines.append(f"Dependencies: {', '.join(sorted(deps))}")

        # Add dependents
        dependents = graph.get_dependents(product_name)
        if dependents:
            lines.append(f"Dependents: {', '.join(sorted(dependents))}")

        return "\n".join(lines)
