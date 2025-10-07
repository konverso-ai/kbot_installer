"""Tests for CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kbot_installer.cli.commands import cli


class TestCLI:
    """Test cases for CLI commands."""

    def test_cli_group_exists(self) -> None:
        """Test that CLI group is properly defined."""
        assert cli.name == "cli"
        assert "Kbot Installer" in cli.help

    def test_cli_version_option(self) -> None:
        """Test that CLI has version option."""
        # Check if version option is present
        options = [option.name for option in cli.params]
        assert "version" in options

    def test_installer_command_exists(self) -> None:
        """Test that installer command exists."""
        commands = [cmd.name for cmd in cli.commands.values()]
        assert "installer" in commands

    def test_list_command_exists(self) -> None:
        """Test that list command exists."""
        commands = [cmd.name for cmd in cli.commands.values()]
        assert "list" in commands


class TestInstallerCommand:
    """Test cases for the 'installer' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("kbot_installer.cli.commands.InstallerService")
    def test_installer_success(self, mock_service_class) -> None:
        """Test successful product installation."""
        # Setup mock
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/test/installer"
        version = "2025.03"
        product = "jira"

        # Run command using CliRunner
        result = self.runner.invoke(
            cli,
            [
                "installer",
                "--installer-dir",
                installer_dir,
                "--version",
                version,
                "--product",
                product,
            ],
        )

        # Assertions
        assert result.exit_code == 0
        mock_service_class.assert_called_once_with(installer_dir)
        mock_service.install.assert_called_once_with(
            product, version, include_dependencies=True
        )

    @patch("kbot_installer.cli.commands.InstallerService")
    def test_installer_with_no_rec(self, mock_service_class) -> None:
        """Test product installation without dependencies."""
        # Setup mock
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/test/installer"
        version = "dev"
        product = "jira"

        # Run command with --no-rec flag
        result = self.runner.invoke(
            cli,
            [
                "installer",
                "--installer-dir",
                installer_dir,
                "--version",
                version,
                "--product",
                product,
                "--no-rec",
            ],
        )

        # Assertions
        assert result.exit_code == 0
        mock_service_class.assert_called_once_with(installer_dir)
        mock_service.install.assert_called_once_with(
            product, version, include_dependencies=False
        )

    @patch("kbot_installer.cli.commands.InstallerService")
    def test_installer_error_handling(self, mock_service_class) -> None:
        """Test error handling in installer command."""
        # Setup mock to raise exception
        mock_service = MagicMock()
        mock_service.install.side_effect = Exception("Test error")
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/test/installer"
        version = "2025.03"
        product = "jira"

        # Run command and expect error
        result = self.runner.invoke(
            cli,
            [
                "installer",
                "--installer-dir",
                installer_dir,
                "--version",
                version,
                "--product",
                product,
            ],
        )

        # Assertions
        assert result.exit_code != 0
        assert "Error installing product" in result.output


class TestListCommand:
    """Test cases for the 'list' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("kbot_installer.cli.commands.InstallerService")
    @patch("kbot_installer.cli.commands.Path")
    def test_list_products_success(self, mock_path_class, mock_service_class) -> None:
        """Test successful product listing."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        mock_service.product_collection = MagicMock()
        mock_service.list_products.return_value = "Product list output"
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/test/installer"

        # Run command using CliRunner
        result = self.runner.invoke(cli, ["list", "--installer-dir", installer_dir])

        # Assertions
        assert result.exit_code == 0
        assert "Product list output" in result.output

    @patch("kbot_installer.cli.commands.InstallerService")
    @patch("kbot_installer.cli.commands.Path")
    def test_list_products_with_tree(self, mock_path_class, mock_service_class) -> None:
        """Test product listing with tree view."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        mock_service.product_collection = MagicMock()
        mock_service.list_products.return_value = "Tree output"
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/test/installer"

        # Run command with --tree flag
        result = self.runner.invoke(
            cli, ["list", "--installer-dir", installer_dir, "--tree"]
        )

        # Assertions
        assert result.exit_code == 0
        assert "Tree output" in result.output

    @patch("kbot_installer.cli.commands.InstallerService")
    @patch("kbot_installer.cli.commands.Path")
    def test_list_products_no_collection(
        self, mock_path_class, mock_service_class
    ) -> None:
        """Test product listing when no collection exists."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        # product_collection property no longer exists
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/test/installer"

        # Run command
        result = self.runner.invoke(cli, ["list", "--installer-dir", installer_dir])

        # Assertions
        assert result.exit_code == 0

    @patch("kbot_installer.cli.commands.InstallerService")
    @patch("kbot_installer.cli.commands.Path")
    def test_list_products_directory_not_exists(
        self, mock_path_class, mock_service_class
    ) -> None:
        """Test product listing when directory doesn't exist."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/nonexistent/installer"

        # Run command
        result = self.runner.invoke(cli, ["list", "--installer-dir", installer_dir])

        # Assertions
        assert result.exit_code == 0
        assert (
            "Installer directory does not exist. No products installed."
            in result.output
        )

    @patch("kbot_installer.cli.commands.InstallerService")
    @patch("kbot_installer.cli.commands.Path")
    def test_list_products_error_handling(
        self, mock_path_class, mock_service_class
    ) -> None:
        """Test error handling in list command."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        mock_service = MagicMock()
        mock_service.product_collection = MagicMock()
        mock_service.list_products.side_effect = Exception("Test error")
        mock_service_class.return_value = mock_service

        # Test data
        installer_dir = "/test/installer"

        # Run command and expect error
        result = self.runner.invoke(cli, ["list", "--installer-dir", installer_dir])

        # Assertions
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
        assert "installer" in result.output
        assert "list" in result.output

    def test_installer_help(self) -> None:
        """Test installer command help."""
        result = self.runner.invoke(cli, ["installer", "--help"])
        assert result.exit_code == 0
        assert "Install a kbot product" in result.output

    def test_list_help(self) -> None:
        """Test list command help."""
        result = self.runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "List installed kbot products" in result.output
