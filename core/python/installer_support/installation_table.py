"""Installation table display for kbot-installer.

This module provides a clean table display for installation results,
showing product name, provider used, and installation status.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from rich.cells import cell_len
from rich.console import Console
from rich.table import Table

InstallationStatus = Literal["success", "error", "skipped", "up_to_date", "kept", "in_progress"]
FinalStatus = Literal["success", "error", "skipped", "kept"]

_PRODUCT_WIDTH = 22
_PROVIDER_WIDTH = 20
_STATUS_WIDTH = 18
_COLUMN_GAP = 2


def _pad(text: str, width: int) -> str:
    """Pad text with spaces up to width terminal cells (emoji take two cells)."""
    return text + " " * max(0, width - cell_len(text))


@dataclass
class InstallationResult:
    """Result of a product installation.

    Attributes:
        product_name: Name of the product installed.
        provider_name: Name of the provider used for installation.
        status: Installation status ('success', 'error', 'skipped', 'up_to_date', 'kept',
            'in_progress'). 'kept' means a local copy (e.g. a manual build) was deliberately
            left untouched; 'up_to_date' is a 'skipped' product reported by a table built
            with ``show_unchanged``.
        error_message: Error message if status is 'error'.
        details: Free-form details shown instead of the default ones.

    """

    product_name: str
    provider_name: str
    status: InstallationStatus
    error_message: str | None = None
    details: str | None = None


class InstallationTable:
    """Table display for installation results.

    This class provides a clean, tabular display of installation results
    showing product name, provider used, and installation status.
    """

    def __init__(self, *, verbose: bool = False, show_unchanged: bool = False) -> None:
        """Initialize the installation table.

        Args:
            verbose: When True, show skipped products and extra details.
            show_unchanged: When True (update context), report 'skipped' products as
                'up_to_date' rows, shown even without verbose.

        """
        self.verbose = verbose
        self.show_unchanged = show_unchanged
        self.console = Console()
        self.results: list[InstallationResult] = []
        self._progress_product: str | None = None
        self._progress_line_width = 0
        self._product_width = _PRODUCT_WIDTH
        self._provider_width = _PROVIDER_WIDTH

    def fit_product_names(self, names: Iterable[str]) -> None:
        """Widen the product column so that every given name fits.

        Call it before the first row when the product names are known upfront:
        the column otherwise only widens when a longer name is printed, which
        leaves the rows already printed narrower.

        Args:
            names: Product names the table will show.

        """
        for name in names:
            self._product_width = max(self._product_width, cell_len(name) + _COLUMN_GAP)

    def begin_installation(self, product_name: str) -> None:
        """Display an in-progress line for a product being installed.

        Args:
            product_name: Name of the product being installed.

        """
        self._progress_product = product_name
        line = self._format_line(product_name, "-", self._get_status_text("in_progress"), "")
        self._progress_line_width = cell_len(line)
        self.console.print(line, end="\r", highlight=False)

    def complete_installation(
        self,
        product_name: str,
        provider_name: str,
        status: FinalStatus,
        error_message: str | None = None,
        details: str | None = None,
    ) -> None:
        """Record and display the final installation result for a product.

        Args:
            product_name: Name of the product.
            provider_name: Name of the provider used.
            status: Final installation status.
            error_message: Error message if status is 'error'.
            details: Free-form details shown instead of the default ones.

        """
        result = InstallationResult(
            product_name=product_name,
            provider_name=provider_name,
            status=self._recorded_status(status),
            error_message=error_message,
            details=details,
        )
        self.results.append(result)

        if result.status == "skipped" and not self.verbose:
            self._clear_progress_line()
            return

        self._print_result_line(result)

    def add_result(
        self,
        product_name: str,
        provider_name: str,
        status: FinalStatus,
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
                status=self._recorded_status(status),
                error_message=error_message,
            )
        )

    def _recorded_status(self, status: FinalStatus) -> InstallationStatus:
        """Return the status recorded for status, given show_unchanged."""
        if status == "skipped" and self.show_unchanged:
            return "up_to_date"
        return status

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
            status_text = self._get_status_text(result.status)

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
        line = self._format_line(
            result.product_name,
            result.provider_name,
            self._get_status_text(result.status),
            self._get_details(result),
        )

        if self._progress_product == result.product_name:
            # Overwrite the whole in-progress line, which may be the longer one.
            self.console.print(_pad(line, self._progress_line_width), highlight=False)
            self._progress_product = None
            self._progress_line_width = 0
            return

        self.console.print(line, highlight=False)

    def _clear_progress_line(self) -> None:
        """Clear an in-progress line without printing a final result."""
        if self._progress_product is None:
            return
        self.console.print(" " * self._progress_line_width, end="\r", highlight=False)
        self._progress_product = None
        self._progress_line_width = 0

    def _format_line(
        self,
        product_name: str,
        provider_name: str,
        status_text: str,
        details: str,
    ) -> str:
        """Format one installation row as fixed-width text.

        Columns are padded by terminal cells, not characters, so that rows
        stay aligned whatever the width of their status icon. A product or
        provider name too long for its column widens it for the next rows.
        """
        self._product_width = max(self._product_width, cell_len(product_name) + _COLUMN_GAP)
        self._provider_width = max(self._provider_width, cell_len(provider_name) + _COLUMN_GAP)
        return (
            _pad(product_name, self._product_width)
            + _pad(provider_name, self._provider_width)
            + _pad(status_text, _STATUS_WIDTH)
            + details
        )

    def _get_status_text(self, status: str) -> str:
        """Return the icon and label shown in the status column (e.g. '✔ Up to date')."""
        return f"{self._get_status_icon(status)} {status.replace('_', ' ').capitalize()}"

    def _get_details(self, result: InstallationResult) -> str:
        """Return the details column for a result."""
        if result.details:
            return result.details
        if result.status == "error" and result.error_message:
            return result.error_message
        if result.status in ("skipped", "up_to_date"):
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
            "up_to_date": "green",
            "kept": "cyan",
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
            "up_to_date": "✔",
            "kept": "📌",
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
        up_to_date_count = sum(1 for r in self.results if r.status == "up_to_date")
        kept_count = sum(1 for r in self.results if r.status == "kept")

        summary_parts = []
        if success_count > 0:
            summary_parts.append(f"{success_count} successful")
        if error_count > 0:
            summary_parts.append(f"{error_count} failed")
        if up_to_date_count > 0:
            summary_parts.append(f"{up_to_date_count} up to date")
        if kept_count > 0:
            summary_parts.append(f"{kept_count} kept (local)")
        if skipped_count > 0 and self.verbose:
            summary_parts.append(f"{skipped_count} skipped")

        if not summary_parts:
            return "Installation complete: nothing to install"

        return f"Installation complete: {', '.join(summary_parts)}"
