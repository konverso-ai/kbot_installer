"""Tests for CLI commands."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from cli.commands import cli
from storage.base import StorageBackendEnum


def _write_product(
    installer_dir: Path,
    name: str,
    *,
    type_: str = "solution",
    parents: list[str] | None = None,
) -> None:
    """Create a product folder with a description.xml under installer_dir."""
    product_dir = installer_dir / name
    product_dir.mkdir(parents=True, exist_ok=True)
    parents_xml = ""
    if parents:
        parent_nodes = "".join(f'<parent name="{p}"/>' for p in parents)
        parents_xml = f"<parents>{parent_nodes}</parents>"
    (product_dir / "description.xml").write_text(
        f'<product name="{name}" type="{type_}">{parents_xml}</product>',
        encoding="utf-8",
    )


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

    def test_only_download_list_and_install_commands(self) -> None:
        """Only the download, list, and install commands should be exposed."""
        commands = {cmd.name for cmd in cli.commands.values()}
        assert commands == {"download", "list", "install"}


class TestDownloadCommand:
    """Test cases for the 'download' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.build_downloadable")
    def test_download_product_success(self, mock_build_downloadable) -> None:
        """A product download builds a downloadable and calls download()."""
        mock_instance = MagicMock()
        mock_build_downloadable.return_value = mock_instance

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
        mock_build_downloadable.assert_called_once()
        call_kwargs = mock_build_downloadable.call_args.kwargs
        assert call_kwargs["product"] == "jira"
        assert call_kwargs["version"] == "2025.03"
        assert call_kwargs["bundle"] is None
        assert call_kwargs["include_dependencies"] is True
        mock_instance.download.assert_called_once()

    @patch("cli.commands.build_downloadable")
    def test_download_with_no_rec(self, mock_build_downloadable) -> None:
        """--no-rec disables dependency download."""
        mock_build_downloadable.return_value = MagicMock()

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
        assert mock_build_downloadable.call_args.kwargs["include_dependencies"] is False

    @patch("cli.commands.build_downloadable")
    def test_download_forwards_selected_providers(self, mock_build_downloadable) -> None:
        """Explicit --provider options are forwarded to build_downloadable."""
        mock_build_downloadable.return_value = MagicMock()

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
        assert mock_build_downloadable.call_args.kwargs["provider"] == ("github", "bitbucket")

    @patch("cli.commands.build_downloadable")
    def test_download_bundle_success(self, mock_build_downloadable) -> None:
        """Bundle mode forwards bundle/storage to build_downloadable, without requiring --version."""
        mock_instance = MagicMock()
        mock_build_downloadable.return_value = mock_instance

        result = self.runner.invoke(
            cli,
            [
                "download",
                "--bundle",
                "ev-basic",
                "--product",
                "kbot",
                "--storage",
                "s3",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_build_downloadable.call_args.kwargs
        assert call_kwargs["bundle"] == "ev-basic"
        assert call_kwargs["version"] is None
        assert call_kwargs["storage_backend"] == StorageBackendEnum.S3
        mock_instance.download.assert_called_once()

    def test_download_product_requires_version(self) -> None:
        """The version option is required in product mode (without --bundle)."""
        result = self.runner.invoke(
            cli,
            ["download", "--product", "kbot"],
        )
        assert result.exit_code != 0
        assert "'-v/--version' is required" in result.output

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

    @patch("cli.commands.build_downloadable")
    def test_download_error_handling(self, mock_build_downloadable) -> None:
        """Download failures are surfaced as an error and abort."""
        mock_instance = MagicMock()
        mock_instance.download.side_effect = Exception("Test error")
        mock_build_downloadable.return_value = mock_instance

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


class TestInstallCommand:
    """Test cases for the 'install' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_product_success(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Installing a product downloads it with dependencies, then builds workarea and db."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        installer_dir = tmp_path / "installer"
        workarea_dir = tmp_path / "work"
        # download() is mocked, so simulate its effect on disk directly.
        _write_product(installer_dir, "jira")

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--secret",
                "K0nversOK!",
                "--installer-dir",
                str(installer_dir),
                "--workarea-dir",
                str(workarea_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert mock_build_downloadable.call_args.kwargs["include_dependencies"] is True
        mock_build_downloadable.return_value.download.assert_called_once_with(installer_dir)
        mock_build_workarea.assert_called_once_with(
            installer_path=installer_dir, workarea_path=workarea_dir
        )
        mock_build_workarea.return_value.install.assert_called_once()
        mock_build_database.assert_called_once()
        assert mock_build_database.call_args.kwargs["db_host"] is None
        assert mock_build_database.call_args.kwargs["pg_dir"] == Path(str(tmp_path / "pg"))
        assert mock_build_database.call_args.kwargs["schema_paths"] == [
            installer_dir / "jira" / "db" / "init" / "db_schema.sql"
        ]

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_product_success_applies_dependency_schemas_first(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Schemas of dependency products are applied before the top level product's."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        installer_dir = tmp_path / "installer"
        workarea_dir = tmp_path / "work"
        # download() is mocked, so simulate its effect on disk directly: a top level
        # product ("site-konverso") depending on a base product ("base-product").
        _write_product(installer_dir, "base-product")
        _write_product(installer_dir, "site-konverso", parents=["base-product"])

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "site-konverso",
                "--version",
                "2025.03-dev",
                "--secret",
                "K0nversOK!",
                "--installer-dir",
                str(installer_dir),
                "--workarea-dir",
                str(workarea_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert mock_build_database.call_args.kwargs["schema_paths"] == [
            installer_dir / "base-product" / "db" / "init" / "db_schema.sql",
            installer_dir / "site-konverso" / "db" / "init" / "db_schema.sql",
        ]

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_bundle_success_without_version(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Bundle mode does not require -v/--version."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--bundle",
                "ev-basic-00018",
                "--product",
                "site-konverso",
                "--secret",
                "K0nversOK!",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_build_downloadable.call_args.kwargs
        assert call_kwargs["bundle"] == "ev-basic-00018"
        assert call_kwargs["version"] is None
        mock_build_downloadable.return_value.download.assert_called_once()

    def test_install_requires_version_without_bundle(self, tmp_path) -> None:
        """-v/--version is required when installing a product without --bundle."""
        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--secret",
                "secret",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code != 0
        assert "Option '-v/--version' is required" in result.output

    @patch("cli.commands.build_downloadable")
    def test_install_aborts_when_workarea_already_exists(
        self, mock_build_downloadable, tmp_path
    ) -> None:
        """Installation is cancelled without downloading anything when the workarea exists."""
        workarea_dir = tmp_path / "work"
        workarea_dir.mkdir()

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--secret",
                "secret",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(workarea_dir),
            ],
        )

        assert result.exit_code != 0
        assert "already exists" in result.output
        mock_build_downloadable.assert_not_called()

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_no_password_generates_random_password(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--no-password generates and displays a random database password."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--secret",
                "secret",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
                "--no-password",
            ],
        )

        assert result.exit_code == 0, result.output
        generated_password = mock_build_database.call_args.kwargs["password"]
        assert generated_password
        assert generated_password != "kbot_db_pwd"
        assert generated_password in result.output

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_external_db_when_db_host_provided(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
    ) -> None:
        """Providing --db-host selects the external database backend (no pg_dir needed)."""
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--secret",
                "secret",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
                "--db-host",
                "external-db.example.com",
            ],
        )

        assert result.exit_code == 0, result.output
        assert mock_build_database.call_args.kwargs["db_host"] == "external-db.example.com"
        assert mock_build_database.call_args.kwargs["pg_dir"] is None

    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_requires_pg_dir_env_for_internal_db(
        self, mock_build_downloadable, mock_build_workarea, tmp_path, monkeypatch
    ) -> None:
        """Internal DB mode fails when neither PG_DIR nor 3rdparty/versions.env is available."""
        monkeypatch.delenv("PG_DIR", raising=False)
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--secret",
                "secret",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code != 0
        assert "PG_DIR" in result.output

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_resolves_pg_dir_from_versions_env(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Without PG_DIR set, PG_DIR is resolved from installer/3rdparty/versions.env."""
        monkeypatch.delenv("PG_DIR", raising=False)
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        installer_dir = tmp_path / "installer"
        thirdparty = installer_dir / "3rdparty"
        (thirdparty / "postgresql-11.5" / "lib").mkdir(parents=True)
        (thirdparty / "versions.env").write_text(
            "THIRDPARTY_PATH=${THIRDPARTY_HOME}\n"
            "PG_VERSION=11.5\n"
            "PG_DIR=${THIRDPARTY_PATH}/postgresql-${PG_VERSION}\n",
            encoding="utf-8",
        )

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--secret",
                "secret",
                "--installer-dir",
                str(installer_dir),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code == 0, result.output
        assert mock_build_database.call_args.kwargs["pg_dir"] == thirdparty / "postgresql-11.5"
        # LD_LIBRARY_PATH is prepended with the existing 3rdparty lib dir.
        expected_lib = str(thirdparty / "postgresql-11.5" / "lib")
        assert expected_lib in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)

    @patch("installer_support.python_requirements.subprocess.run")
    @patch("installer_support.python_requirements.InstallerService")
    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_runs_pip3_for_solution_products(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        mock_installer_service_cls,
        mock_subprocess_run,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Solution/customer products with a requirements.txt are installed via pip3.sh."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        installer_dir = tmp_path / "installer"
        pip3 = installer_dir / "kbot" / "bin" / "pip3.sh"
        pip3.parent.mkdir(parents=True)
        pip3.write_text("#!/bin/bash\n", encoding="utf-8")
        req = installer_dir / "acme" / "requirements.txt"
        req.parent.mkdir(parents=True)
        req.write_text("requests\n", encoding="utf-8")

        framework = MagicMock()
        framework.name = "kbot"
        framework.type = "framework"
        solution = MagicMock()
        solution.name = "acme"
        solution.type = "solution"
        mock_installer_service_cls.return_value.load_products_from_disk.return_value = [
            framework,
            solution,
        ]

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "acme",
                "--version",
                "2025.03-dev",
                "--secret",
                "secret",
                "--installer-dir",
                str(installer_dir),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code == 0, result.output
        mock_subprocess_run.assert_called_once()
        called_cmd = mock_subprocess_run.call_args.args[0]
        assert called_cmd[0] == str(pip3)
        assert "install" in called_cmd
        assert str(req) in called_cmd

    @patch("cli.commands.install_product_python_requirements")
    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_skip_python_requirements(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        mock_install_python_requirements,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--skip-python-requirements bypasses the pip3.sh installation step."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "acme",
                "--version",
                "2025.03-dev",
                "--secret",
                "secret",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
                "--skip-python-requirements",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_install_python_requirements.assert_not_called()


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
        assert "install" in result.output

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

    def test_install_help(self) -> None:
        """Test install command help."""
        result = self.runner.invoke(cli, ["install", "--help"])
        assert result.exit_code == 0
        assert "Install a kbot product or bundle" in result.output


class TestInstallShellWrapper:
    """Regression tests for the bin/install.sh wrapper.

    Guards against reintroducing the chicken-and-egg dependency where install.sh
    sourced kbot/bin/env.sh (before kbot was downloaded), leaking kbot's
    PYTHONPATH into the isolated kbot-installer interpreter and causing package
    collisions (e.g. `utils` -> `ModuleNotFoundError: No module named 'magic'`).
    """

    @staticmethod
    def _install_sh() -> Path:
        # core/python/cli/tests/test_commands.py -> repo root is five parents up.
        return Path(__file__).resolve().parents[4] / "bin" / "install.sh"

    def test_wrapper_exists(self) -> None:
        """The wrapper script is present."""
        assert self._install_sh().is_file()

    def test_wrapper_does_not_source_kbot_env(self) -> None:
        """The wrapper must not source any kbot env.sh script."""
        content = self._install_sh().read_text(encoding="utf-8")
        code_lines = [
            line for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")
        ]
        code = "\n".join(code_lines)
        assert "env.sh" not in code
        assert "source" not in code

    def test_wrapper_does_not_set_pythonpath(self) -> None:
        """The wrapper must not export or mutate PYTHONPATH."""
        content = self._install_sh().read_text(encoding="utf-8")
        code_lines = [
            line for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")
        ]
        code = "\n".join(code_lines)
        assert "PYTHONPATH" not in code
