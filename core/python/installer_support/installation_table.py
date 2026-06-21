"""Installation table display for kbot-installer.

This module provides a clean table display for installation results,
showing product name, provider used, and installation status.
"""

from dataclasses import dataclass
from typing import Literal

from rich.console import Console
from rich.table import Table

InstallationStatus = Literal["success", "error", "skipped", "in_progress"]

_PRODUCT_WIDTH = 22
_PROVIDER_WIDTH = 18
_STATUS_WIDTH = 18


@dataclass
class InstallationResult:
    """Result of a product installation.

    Attributes:
        product_name: Name of the product installed.
        provider_name: Name of the provider used for installation.
        status: Installation status ('success', 'error', 'skipped', 'in_progress').
        error_message: Error message if status is 'error'.

    """

    product_name: str
    provider_name: str
    status: InstallationStatus
    error_message: str | None = None


class InstallationTable:
    """Table display for installation results.

    This class provides a clean, tabular display of installation results
    showing product name, provider used, and installation status.
    """

    def __init__(self, *, verbose: bool = False) -> None:
        """Initialize the installation table.

        Args:
            verbose: When True, show skipped products and extra details.

        """
        self.verbose = verbose
        self.console = Console()
        self.results: list[InstallationResult] = []
        self._progress_product: str | None = None
        self._progress_line_width = 0

    def begin_installation(self, product_name: str) -> None:
        """Display an in-progress line for a product being installed.

        Args:
            product_name: Name of the product being installed.

        """
        self._progress_product = product_name
        line = self._format_line(product_name, "-", "⏳ In progress", "")
        self._progress_line_width = len(line)
        self.console.print(line, end="\r", highlight=False)

    def complete_installation(
        self,
        product_name: str,
        provider_name: str,
        status: Literal["success", "error", "skipped"],
        error_message: str | None = None,
    ) -> None:
        """Record and display the final installation result for a product.

        Args:
            product_name: Name of the product.
            provider_name: Name of the provider used.
            status: Final installation status.
            error_message: Error message if status is 'error'.

        """
        result = InstallationResult(
            product_name=product_name,
            provider_name=provider_name,
            status=status,
            error_message=error_message,
        )
        self.results.append(result)

        if status == "skipped" and not self.verbose:
            self._clear_progress_line()
            return

        self._print_result_line(result)

    def add_result(
        self,
        product_name: str,
        provider_name: str,
        status: Literal["success", "error", "skipped"],
        error_message: str | None = None,
        *,
        display_immediately: bool = False,
    ) -> None:
        """Add an installation result to the table.

        Args:
            product_name: Name of the product.
            provider_name: Name of the provider used.
            status: Installation status.
            error_message: Error message if status is 'error'.
            display_immediately: Whether to display the result immediately.

        """
        if display_immediately:
            self.complete_installation(
                product_name,
                provider_name,
                status,
                error_message,
            )
            return

        self.results.append(
            InstallationResult(
                product_name=product_name,
                provider_name=provider_name,
                status=status,
                error_message=error_message,
            )
        )

    def display(self) -> None:
        """Display the installation results table."""
        if not self.results:
            self.console.print("No installation results to display.")
            return

        table = Table(title="Installation Results")
        table.add_column("Product", style="cyan", no_wrap=True)
        table.add_column("Provider", style="magenta")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")

        for result in self.results:
            if result.status == "skipped" and not self.verbose:
                continue

            status_style = self._get_status_style(result.status)
            status_icon = self._get_status_icon(result.status)
            status_text = f"{status_icon} {result.status.replace('_', ' ').title()}"

            details = self._get_details(result)

            table.add_row(
                result.product_name,
                result.provider_name,
                status_text,
                details,
                style=status_style,
            )

        self.console.print(table)

    def _print_result_line(self, result: InstallationResult) -> None:
        """Print a single formatted result line."""
        status_icon = self._get_status_icon(result.status)
        status_text = f"{status_icon} {result.status.replace('_', ' ').title()}"
        details = self._get_details(result)
        line = self._format_line(
            result.product_name,
            result.provider_name,
            status_text,
            details,
        )

        if self._progress_product == result.product_name:
            padded_line = line.ljust(max(self._progress_line_width, len(line)))
            self.console.print(padded_line, highlight=False)
            self._progress_product = None
            self._progress_line_width = 0
            return

        self.console.print(line, highlight=False)

    def _clear_progress_line(self) -> None:
        """Clear an in-progress line without printing a final result."""
        if self._progress_product is None:
            return
        self.console.print(" " * self._progress_line_width, end="\r", highlight=False)
        self.console.print("", highlight=False)
        self._progress_product = None
        self._progress_line_width = 0

    def _format_line(
        self,
        product_name: str,
        provider_name: str,
        status_text: str,
        details: str,
    ) -> str:
        """Format one installation row as fixed-width text."""
        return (
            f"{product_name:<{_PRODUCT_WIDTH}}"
            f"{provider_name:<{_PROVIDER_WIDTH}}"
            f"{status_text:<{_STATUS_WIDTH}}"
            f"{details}"
        )

    def _get_details(self, result: InstallationResult) -> str:
        """Return the details column for a result."""
        if result.status == "error" and result.error_message:
            return result.error_message
        if result.status == "skipped":
            return "Already installed"
        return ""

    def _get_status_style(self, status: str) -> str:
        """Get the style for a status.

        Args:
            status: Status string.

        Returns:
            Style string for the status.

        """
        styles = {
            "success": "green",
            "error": "red",
            "skipped": "yellow",
            "in_progress": "blue",
        }
        return styles.get(status, "white")

    def _get_status_icon(self, status: str) -> str:
        """Get the icon for a status.

        Args:
            status: Status string.

        Returns:
            Icon string for the status.

        """
        icons = {
            "success": "✅",
            "error": "❌",
            "skipped": "⏭️",
            "in_progress": "⏳",
        }
        return icons.get(status, "❓")

    def get_summary(self) -> str:
        """Get a summary of installation results.

        Returns:
            Summary string with counts of each status.

        """
        if not self.results:
            return "No installations performed."

        success_count = sum(1 for r in self.results if r.status == "success")
        error_count = sum(1 for r in self.results if r.status == "error")
        skipped_count = sum(1 for r in self.results if r.status == "skipped")

        summary_parts = []
        if success_count > 0:
            summary_parts.append(f"{success_count} successful")
        if error_count > 0:
            summary_parts.append(f"{error_count} failed")
        if skipped_count > 0 and self.verbose:
            summary_parts.append(f"{skipped_count} skipped")

        if not summary_parts:
            return "Installation complete: nothing to install"

        return f"Installation complete: {', '.join(summary_parts)}"
