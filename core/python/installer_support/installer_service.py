"""InstallerService for listing installed products."""

from pathlib import Path

from installable.dependency_graph import DependencyGraph
from installable.renderer import DependencyTreeRenderer
from installer_support.installation_table import InstallationTable
from utils.Logger import logger
from utils.product.product import Product

log = logger.get_package_logger("installer_support")


class InstallerService:
    """Service for inspecting kbot products in the installer directory.

    Product and bundle downloads are handled by the ``downloadable`` package;
    this service only reads already-downloaded products from disk to support
    the ``list`` CLI command.

    Attributes:
        installer_dir: Path to the installer directory.

    """

    def __init__(
        self,
        installer_dir: str | Path,
        *,
        verbose: bool = False,
    ) -> None:
        """Initialize the installer service.

        Args:
            installer_dir: Path to the installer directory.
            verbose: When True, show detailed output.

        """
        self.installer_dir = Path(installer_dir)
        self.verbose = verbose
        self.installation_table = InstallationTable(verbose=verbose)

    def list_products(self, *, as_tree: bool = False, verbose: bool = False) -> str:
        """List products installed in the installer directory.

        Args:
            as_tree: Whether to render products as a dependency tree.
            verbose: Show all subtrees even if already displayed.

        Returns:
            Formatted string listing the installed products.

        """
        log.info("Listing installed products (tree: %s)", as_tree)

        products = self._load_products_from_disk()
        if not products:
            return "No products installed."

        if as_tree:
            graph = DependencyGraph(products)
            renderer = DependencyTreeRenderer()
            return renderer.render_uv_tree_style(graph, verbose=verbose)

        lines = ["Installed products:", "=================="]
        for product in products:
            lines.append(f"- {product.name} ({product.type})")
            if product.parent_names:
                lines.append(f"  Dependencies: {', '.join(product.parent_names)}")
        return "\n".join(lines)

    def get_installation_table(self) -> InstallationTable:
        """Return the installation results table.

        Returns:
            InstallationTable containing installation results.

        """
        return self.installation_table

    def _load_products_from_disk(self) -> list[Product]:
        """Load Product objects from the installer directory.

        Each immediate subdirectory holding a ``description.xml`` is loaded as a
        product; a sibling ``description.json`` is merged when present.

        Returns:
            The products discovered in the installer directory.

        """
        products: list[Product] = []
        if not self.installer_dir.exists():
            return products

        for item in sorted(self.installer_dir.iterdir()):
            description_xml = item / "description.xml"
            if not item.is_dir() or not description_xml.exists():
                continue
            try:
                product = Product.from_xml_file(description_xml)
                description_json = item / "description.json"
                if description_json.exists():
                    product = Product.merge(
                        product, Product.from_json_file(description_json)
                    )
            except Exception as e:
                log.debug("Failed to load product from %s: %s", item, e)
                continue
            products.append(product)

        return products
