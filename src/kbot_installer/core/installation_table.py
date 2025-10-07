"""Installation table display for kbot-installer.

This module provides a clean table display for installation results,
showing product name, provider used, and installation status.
"""

from dataclasses import dataclass
from typing import Literal

from rich.console import Console
from rich.table import Table


@dataclass
class InstallationResult:
    """Result of a product installation.

    Attributes:
        product_name: Name of the product installed.
        provider_name: Name of the provider used for installation.
        status: Installation status ('success', 'error', 'skipped').
        error_message: Error message if status is 'error'.

    """

    product_name: str
    provider_name: str
    status: Literal["success", "error", "skipped"]
    error_message: str | None = None


class InstallationTable:
    """Table display for installation results.

    This class provides a clean, tabular display of installation results
    showing product name, provider used, and installation status.
    """

    def __init__(self) -> None:
        """Initialize the installation table."""
        self.console = Console()
        self.results: list[InstallationResult] = []

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
        result = InstallationResult(
            product_name=product_name,
            provider_name=provider_name,
            status=status,
            error_message=error_message,
        )
        self.results.append(result)

        if display_immediately:
            self._display_single_result(result)

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
            status_style = self._get_status_style(result.status)
            status_icon = self._get_status_icon(result.status)
            status_text = f"{status_icon} {result.status.title()}"

            details = ""
            if result.status == "error" and result.error_message:
                details = result.error_message
            elif result.status == "skipped":
                details = "Already installed"

            table.add_row(
                result.product_name,
                result.provider_name,
                status_text,
                details,
                style=status_style,
            )

        self.console.print(table)

    def _display_single_result(self, result: InstallationResult) -> None:
        """Display a single installation result immediately.

        Args:
            result: The installation result to display.

        """
        status_style = self._get_status_style(result.status)
        status_icon = self._get_status_icon(result.status)
        status_text = f"{status_icon} {result.status.title()}"

        details = ""
        if result.status == "error" and result.error_message:
            details = result.error_message
        elif result.status == "skipped":
            details = "Already installed"

        # Create a simple table for single result display
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Product", style="cyan", no_wrap=True, width=20)
        table.add_column("Provider", style="magenta", width=15)
        table.add_column("Status", justify="center", width=15)
        table.add_column("Details", style="dim", width=30)

        table.add_row(
            result.product_name,
            result.provider_name,
            status_text,
            details,
            style=status_style,
        )

        self.console.print(table)

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
        if skipped_count > 0:
            summary_parts.append(f"{skipped_count} skipped")

        return f"Installation complete: {', '.join(summary_parts)}"
