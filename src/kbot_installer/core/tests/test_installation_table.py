"""Tests for installation_table module."""

from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.installation_table import (
    InstallationResult,
    InstallationTable,
)


class TestInstallationResult:
    """Test cases for InstallationResult dataclass."""

    def test_installation_result_creation(self) -> None:
        """Test that InstallationResult can be created with required fields."""
        result = InstallationResult(
            product_name="test-product", provider_name="github", status="success"
        )

        assert result.product_name == "test-product"
        assert result.provider_name == "github"
        assert result.status == "success"
        assert result.error_message is None

    def test_installation_result_with_error_message(self) -> None:
        """Test that InstallationResult can be created with error message."""
        result = InstallationResult(
            product_name="test-product",
            provider_name="github",
            status="error",
            error_message="Connection failed",
        )

        assert result.product_name == "test-product"
        assert result.provider_name == "github"
        assert result.status == "error"
        assert result.error_message == "Connection failed"

    def test_installation_result_all_statuses(self) -> None:
        """Test that InstallationResult works with all status types."""
        success_result = InstallationResult("prod1", "provider1", "success")
        error_result = InstallationResult("prod2", "provider2", "error", "Error msg")
        skipped_result = InstallationResult("prod3", "provider3", "skipped")

        assert success_result.status == "success"
        assert error_result.status == "error"
        assert skipped_result.status == "skipped"


class TestInstallationTable:
    """Test cases for InstallationTable class."""

    @pytest.fixture
    def installation_table(self) -> InstallationTable:
        """Create an InstallationTable for testing."""
        return InstallationTable()

    def test_initialization(self, installation_table) -> None:
        """Test that InstallationTable initializes correctly."""
        assert installation_table.results == []
        assert hasattr(installation_table, "console")

    def test_add_result_success(self, installation_table) -> None:
        """Test adding a successful installation result."""
        installation_table.add_result(
            product_name="test-product", provider_name="github", status="success"
        )

        assert len(installation_table.results) == 1
        result = installation_table.results[0]
        assert result.product_name == "test-product"
        assert result.provider_name == "github"
        assert result.status == "success"
        assert result.error_message is None

    def test_add_result_error(self, installation_table) -> None:
        """Test adding an error installation result."""
        installation_table.add_result(
            product_name="test-product",
            provider_name="github",
            status="error",
            error_message="Connection failed",
        )

        assert len(installation_table.results) == 1
        result = installation_table.results[0]
        assert result.product_name == "test-product"
        assert result.provider_name == "github"
        assert result.status == "error"
        assert result.error_message == "Connection failed"

    def test_add_result_skipped(self, installation_table) -> None:
        """Test adding a skipped installation result."""
        installation_table.add_result(
            product_name="test-product", provider_name="github", status="skipped"
        )

        assert len(installation_table.results) == 1
        result = installation_table.results[0]
        assert result.product_name == "test-product"
        assert result.provider_name == "github"
        assert result.status == "skipped"
        assert result.error_message is None

    def test_add_multiple_results(self, installation_table) -> None:
        """Test adding multiple installation results."""
        installation_table.add_result("prod1", "provider1", "success")
        installation_table.add_result("prod2", "provider2", "error", "Error msg")
        installation_table.add_result("prod3", "provider3", "skipped")

        assert len(installation_table.results) == 3
        assert installation_table.results[0].status == "success"
        assert installation_table.results[1].status == "error"
        assert installation_table.results[2].status == "skipped"

    @patch("kbot_installer.core.installation_table.Console")
    def test_display_empty_results(
        self, mock_console_class, installation_table
    ) -> None:
        """Test displaying empty results."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        installation_table.console = mock_console

        installation_table.display()

        mock_console.print.assert_called_once_with(
            "No installation results to display."
        )

    @patch("kbot_installer.core.installation_table.Console")
    @patch("kbot_installer.core.installation_table.Table")
    def test_display_with_results(
        self, mock_table_class, mock_console_class, installation_table
    ) -> None:
        """Test displaying results with data."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        installation_table.console = mock_console

        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        # Add test results
        installation_table.add_result("prod1", "github", "success")
        installation_table.add_result("prod2", "nexus", "error", "Connection failed")
        installation_table.add_result("prod3", "bitbucket", "skipped")

        installation_table.display()

        # Verify table creation
        mock_table_class.assert_called_once_with(title="Installation Results")

        # Verify columns were added
        expected_calls = [
            (("Product",), {"style": "cyan", "no_wrap": True}),
            (("Provider",), {"style": "magenta"}),
            (("Status",), {"justify": "center"}),
            (("Details",), {"style": "dim"}),
        ]
        for call in expected_calls:
            mock_table.add_column.assert_any_call(*call[0], **call[1])

        # Verify rows were added
        assert mock_table.add_row.call_count == 3

        # Verify console print
        mock_console.print.assert_called_once_with(mock_table)

    def test_get_status_style(self, installation_table) -> None:
        """Test getting status styles."""
        assert installation_table._get_status_style("success") == "green"
        assert installation_table._get_status_style("error") == "red"
        assert installation_table._get_status_style("skipped") == "yellow"
        assert installation_table._get_status_style("unknown") == "white"

    def test_get_status_icon(self, installation_table) -> None:
        """Test getting status icons."""
        assert installation_table._get_status_icon("success") == "✅"
        assert installation_table._get_status_icon("error") == "❌"
        assert installation_table._get_status_icon("skipped") == "⏭️"
        assert installation_table._get_status_icon("unknown") == "❓"

    def test_get_summary_empty_results(self, installation_table) -> None:
        """Test getting summary with no results."""
        summary = installation_table.get_summary()
        assert summary == "No installations performed."

    def test_get_summary_success_only(self, installation_table) -> None:
        """Test getting summary with only successful installations."""
        installation_table.add_result("prod1", "provider1", "success")
        installation_table.add_result("prod2", "provider2", "success")

        summary = installation_table.get_summary()
        assert summary == "Installation complete: 2 successful"

    def test_get_summary_error_only(self, installation_table) -> None:
        """Test getting summary with only failed installations."""
        installation_table.add_result("prod1", "provider1", "error", "Error 1")
        installation_table.add_result("prod2", "provider2", "error", "Error 2")

        summary = installation_table.get_summary()
        assert summary == "Installation complete: 2 failed"

    def test_get_summary_skipped_only(self, installation_table) -> None:
        """Test getting summary with only skipped installations."""
        installation_table.add_result("prod1", "provider1", "skipped")
        installation_table.add_result("prod2", "provider2", "skipped")

        summary = installation_table.get_summary()
        assert summary == "Installation complete: 2 skipped"

    def test_get_summary_mixed_results(self, installation_table) -> None:
        """Test getting summary with mixed results."""
        installation_table.add_result("prod1", "provider1", "success")
        installation_table.add_result("prod2", "provider2", "error", "Error")
        installation_table.add_result("prod3", "provider3", "skipped")
        installation_table.add_result("prod4", "provider4", "success")

        summary = installation_table.get_summary()
        assert "2 successful" in summary
        assert "1 failed" in summary
        assert "1 skipped" in summary

    def test_get_summary_single_of_each(self, installation_table) -> None:
        """Test getting summary with one of each status."""
        installation_table.add_result("prod1", "provider1", "success")
        installation_table.add_result("prod2", "provider2", "error", "Error")
        installation_table.add_result("prod3", "provider3", "skipped")

        summary = installation_table.get_summary()
        assert summary == "Installation complete: 1 successful, 1 failed, 1 skipped"

    def test_get_summary_order(self, installation_table) -> None:
        """Test that summary shows results in expected order (success, error, skipped)."""
        installation_table.add_result("prod1", "provider1", "skipped")
        installation_table.add_result("prod2", "provider2", "error", "Error")
        installation_table.add_result("prod3", "provider3", "success")

        summary = installation_table.get_summary()
        # Should be in order: successful, failed, skipped
        assert summary == "Installation complete: 1 successful, 1 failed, 1 skipped"

    def test_display_row_creation_with_error_message(self, installation_table) -> None:
        """Test that display creates rows correctly with error messages."""
        with (
            patch(
                "kbot_installer.core.installation_table.Console"
            ) as mock_console_class,
            patch("kbot_installer.core.installation_table.Table") as mock_table_class,
        ):
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console
            installation_table.console = mock_console

            mock_table = MagicMock()
            mock_table_class.return_value = mock_table

            # Add error result
            installation_table.add_result(
                "prod1", "github", "error", "Connection timeout"
            )
            installation_table.display()

            # Verify add_row was called with correct parameters
            mock_table.add_row.assert_called_once()
            call_args = mock_table.add_row.call_args

            # Check the arguments passed to add_row
            assert call_args[0][0] == "prod1"  # product_name
            assert call_args[0][1] == "github"  # provider_name
            assert "Error" in call_args[0][2]  # status_text (contains "Error")
            assert call_args[0][3] == "Connection timeout"  # details (error_message)

    def test_display_row_creation_with_skipped(self, installation_table) -> None:
        """Test that display creates rows correctly for skipped installations."""
        with (
            patch(
                "kbot_installer.core.installation_table.Console"
            ) as mock_console_class,
            patch("kbot_installer.core.installation_table.Table") as mock_table_class,
        ):
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console
            installation_table.console = mock_console

            mock_table = MagicMock()
            mock_table_class.return_value = mock_table

            # Add skipped result
            installation_table.add_result("prod1", "github", "skipped")
            installation_table.display()

            # Verify add_row was called with correct parameters
            mock_table.add_row.assert_called_once()
            call_args = mock_table.add_row.call_args

            # Check the arguments passed to add_row
            assert call_args[0][0] == "prod1"  # product_name
            assert call_args[0][1] == "github"  # provider_name
            assert "Skipped" in call_args[0][2]  # status_text (contains "Skipped")
            assert call_args[0][3] == "Already installed"  # details

    def test_display_row_creation_with_success(self, installation_table) -> None:
        """Test that display creates rows correctly for successful installations."""
        with (
            patch(
                "kbot_installer.core.installation_table.Console"
            ) as mock_console_class,
            patch("kbot_installer.core.installation_table.Table") as mock_table_class,
        ):
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console
            installation_table.console = mock_console

            mock_table = MagicMock()
            mock_table_class.return_value = mock_table

            # Add success result
            installation_table.add_result("prod1", "github", "success")
            installation_table.display()

            # Verify add_row was called with correct parameters
            mock_table.add_row.assert_called_once()
            call_args = mock_table.add_row.call_args

            # Check the arguments passed to add_row
            assert call_args[0][0] == "prod1"  # product_name
            assert call_args[0][1] == "github"  # provider_name
            assert "Success" in call_args[0][2]  # status_text (contains "Success")
            assert call_args[0][3] == ""  # details (empty for success)

    def test_display_style_application(self, installation_table) -> None:
        """Test that display applies correct styles to rows."""
        with (
            patch(
                "kbot_installer.core.installation_table.Console"
            ) as mock_console_class,
            patch("kbot_installer.core.installation_table.Table") as mock_table_class,
        ):
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console
            installation_table.console = mock_console

            mock_table = MagicMock()
            mock_table_class.return_value = mock_table

            # Add results with different statuses
            installation_table.add_result("prod1", "github", "success")
            installation_table.add_result("prod2", "nexus", "error", "Error")
            installation_table.add_result("prod3", "bitbucket", "skipped")

            installation_table.display()

            # Verify add_row was called 3 times with correct styles
            assert mock_table.add_row.call_count == 3

            # Check that style parameter was passed correctly
            calls = mock_table.add_row.call_args_list
            for call in calls:
                # Each call should have a style parameter
                assert "style" in call[1] or len(call[0]) >= 5
