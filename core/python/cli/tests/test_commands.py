"""Tests for CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cli.commands import cli
from storage.base import StorageBackendEnum


class TestCLI:
    """Test cases for CLI commands."""

    def test_cli_group_exists(self) -> None:
        """Test that CLI group is properly defined."""
        assert cli.name == "cli"
        assert "Kbot Installer" in cli.help

    def test_cli_version_option(self) -> None:
        """Test that CLI has version option."""
        options = [option.name for option in cli.params]
        assert "version" in options

    def test_only_download_and_list_commands(self) -> None:
        """Only the download and list commands should be exposed."""
        commands = {cmd.name for cmd in cli.commands.values()}
        assert commands == {"download", "list"}


class TestDownloadCommand:
    """Test cases for the 'download' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.add_provider")
    @patch("cli.commands.ProductDownloadable")
    def test_download_product_success(
        self, mock_downloadable_cls, mock_add_provider
    ) -> None:
        """A product download builds a ProductDownloadable and calls download()."""
        mock_instance = MagicMock()
        mock_downloadable_cls.return_value = mock_instance
        mock_add_provider.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "download",
                "--installer-dir",
                "/test/installer",
                "--version",
                "2025.03",
                "--product",
                "jira",
            ],
        )

        assert result.exit_code == 0
        mock_downloadable_cls.assert_called_once()
        call_kwargs = mock_downloadable_cls.call_args.kwargs
        assert call_kwargs["product"].name == "jira"
        assert call_kwargs["provider"] is mock_add_provider.return_value
        assert call_kwargs["include_dependencies"] is True
        mock_instance.download.assert_called_once()

    @patch("cli.commands.add_provider")
    @patch("cli.commands.ProductDownloadable")
    def test_download_with_no_rec(
        self, mock_downloadable_cls, mock_add_provider
    ) -> None:
        """--no-rec disables dependency download."""
        mock_downloadable_cls.return_value = MagicMock()
        mock_add_provider.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "download",
                "--version",
                "dev",
                "--product",
                "jira",
                "--no-rec",
            ],
        )

        assert result.exit_code == 0
        assert mock_downloadable_cls.call_args.kwargs["include_dependencies"] is False

    @patch("cli.commands.add_provider")
    @patch("cli.commands.ProductDownloadable")
    def test_download_forwards_selected_providers(
        self, mock_downloadable_cls, mock_add_provider
    ) -> None:
        """Explicit --provider options are forwarded to the selector provider."""
        mock_downloadable_cls.return_value = MagicMock()
        mock_add_provider.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "download",
                "--version",
                "2025.03",
                "--product",
                "jira",
                "--provider",
                "github",
                "--provider",
                "bitbucket",
            ],
        )

        assert result.exit_code == 0
        mock_add_provider.assert_called_once_with(
            name="selector", providers=["github", "bitbucket"]
        )

    @patch("cli.commands.BundleDownloadable")
    def test_download_bundle_success(self, mock_bundle_cls) -> None:
        """Bundle mode builds a BundleDownloadable with the storage backend."""
        mock_instance = MagicMock()
        mock_bundle_cls.return_value = mock_instance

        result = self.runner.invoke(
            cli,
            [
                "download",
                "--bundle",
                "ev-basic",
                "--version",
                "2025.03",
                "--product",
                "kbot",
                "--storage",
                "s3",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_bundle_cls.call_args.kwargs
        assert call_kwargs["storage_name"] == StorageBackendEnum.S3
        assert call_kwargs["name"] == "ev-basic"
        mock_instance.download.assert_called_once()

    def test_download_requires_product(self) -> None:
        """The product option is required."""
        result = self.runner.invoke(
            cli,
            ["download", "--version", "2025.03"],
        )
        assert result.exit_code != 0

    def test_download_rejects_invalid_provider(self) -> None:
        """Invalid provider values are rejected by click."""
        result = self.runner.invoke(
            cli,
            [
                "download",
                "--version",
                "2025.03",
                "--product",
                "jira",
                "--provider",
                "gitlab",
            ],
        )
        assert result.exit_code != 0

    def test_download_rejects_invalid_storage(self) -> None:
        """Invalid storage values are rejected by click."""
        result = self.runner.invoke(
            cli,
            [
                "download",
                "--version",
                "2025.03",
                "--product",
                "jira",
                "--storage",
                "minio",
            ],
        )
        assert result.exit_code != 0

    @patch("cli.commands.add_provider")
    @patch("cli.commands.ProductDownloadable")
    def test_download_error_handling(
        self, mock_downloadable_cls, mock_add_provider
    ) -> None:
        """Download failures are surfaced as an error and abort."""
        mock_instance = MagicMock()
        mock_instance.download.side_effect = Exception("Test error")
        mock_downloadable_cls.return_value = mock_instance
        mock_add_provider.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "download",
                "--version",
                "2025.03",
                "--product",
                "jira",
            ],
        )

        assert result.exit_code != 0
        assert "Error installing product" in result.output


class TestListCommand:
    """Test cases for the 'list' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.InstallerService")
    @patch("cli.commands.Path")
    def test_list_products_success(self, mock_path_class, mock_service_class) -> None:
        """Test successful product listing."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        mock_service.list_products.return_value = "Product list output"
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(cli, ["list", "--installer-dir", "/test/installer"])

        assert result.exit_code == 0
        assert "Product list output" in result.output

    @patch("cli.commands.InstallerService")
    @patch("cli.commands.Path")
    def test_list_products_with_tree(self, mock_path_class, mock_service_class) -> None:
        """Test product listing with tree view."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        mock_service.list_products.return_value = "Tree output"
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(
            cli, ["list", "--installer-dir", "/test/installer", "--tree"]
        )

        assert result.exit_code == 0
        assert "Tree output" in result.output
        mock_service.list_products.assert_called_once_with(as_tree=True, verbose=False)

    @patch("cli.commands.InstallerService")
    @patch("cli.commands.Path")
    def test_list_products_directory_not_exists(
        self, mock_path_class, mock_service_class
    ) -> None:
        """Test product listing when directory doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        mock_service_class.return_value = MagicMock()

        result = self.runner.invoke(
            cli, ["list", "--installer-dir", "/nonexistent/installer"]
        )

        assert result.exit_code == 0
        assert (
            "Installer directory does not exist. No products installed."
            in result.output
        )

    @patch("cli.commands.InstallerService")
    @patch("cli.commands.Path")
    def test_list_products_error_handling(
        self, mock_path_class, mock_service_class
    ) -> None:
        """Test error handling in list command."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        mock_service.list_products.side_effect = Exception("Test error")
        mock_service_class.return_value = mock_service

        result = self.runner.invoke(cli, ["list", "--installer-dir", "/test/installer"])

        assert result.exit_code != 0
        assert "Error listing products" in result.output


class TestCommandIntegration:
    """Integration tests for CLI commands."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_help(self) -> None:
        """Test CLI help output."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Kbot Installer" in result.output
        assert "download" in result.output
        assert "list" in result.output

    def test_download_help(self) -> None:
        """Test download command help."""
        result = self.runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0
        assert (
            "Download kbot products from a product version or a bundle descriptor"
            in result.output
        )

    def test_list_help(self) -> None:
        """Test list command help."""
        result = self.runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "List installed kbot products" in result.output
