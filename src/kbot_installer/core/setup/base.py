"""Base class for setup managers."""

from pathlib import Path
from typing import Any

from kbot_installer.core.interactivity.base import InteractivePrompter
from kbot_installer.core.utils import ensure_directory as ensure_dir_util


class BaseSetupManager:
    """Base class for all setup managers.

    Provides common functionality for creating directories and managing
    setup operations. Uses InteractivePrompter for user interaction.

    Attributes:
        target: Target workarea directory path.
        products: Product collection (ProductList or ProductCollection).
        prompter: InteractivePrompter instance for user interaction.
        update_mode: If True, operates in update mode (validates existing setup).

    """

    def __init__(
        self,
        target: str | Path,
        products: Any,  # ProductList ou ProductCollection
        prompter: InteractivePrompter | None = None,
        *,
        update_mode: bool = False,
        silent_mode: bool = False,
    ) -> None:
        """Initialize base setup manager.

        Args:
            target: Target workarea directory path.
            products: Product collection (ProductList or compatible).
            prompter: Optional InteractivePrompter for user interaction.
            update_mode: Enable update/validation mode.
            silent_mode: Suppress interactive prompts.
        """
        self.target = Path(target)
        self.products = products
        self.prompter = prompter or InteractivePrompter(
            use_defaults=False, silent=silent_mode
        )
        self.update_mode = update_mode
        self.silent_mode = silent_mode

    def setup(self) -> None:
        """Perform the setup operation.

        This method should be overridden by subclasses to implement
        their specific setup logic.
        """
        raise NotImplementedError("Subclasses must implement setup()")

    def ensure_directory(self, path: str | Path) -> Path:
        """Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path (relative to target or absolute).

        Returns:
            Path object of the created directory.
        """
        dir_path = self.target / path if not Path(path).is_absolute() else Path(path)
        ensure_dir_util(dir_path)
        return dir_path

    def get_kbot_product(self) -> Any:
        """Get the kbot product from the collection.

        Returns:
            Kbot product instance.

        Raises:
            AttributeError: If products collection doesn't have kbot() method.
            RuntimeError: If kbot product not found.
        """
        if hasattr(self.products, "kbot"):
            return self.products.kbot()
        # Fallback: search for product named 'kbot'
        for product in self.products:
            if hasattr(product, "name") and product.name == "kbot":
                return product
        raise RuntimeError("kbot product not found in collection")
