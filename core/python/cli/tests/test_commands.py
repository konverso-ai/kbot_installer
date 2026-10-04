"""Tests for CLI commands."""

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.commands import cli
from storage.base import StorageBackendEnum
from updatable.factory import UpdatableName


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

    def test_only_expected_commands_are_exposed(self) -> None:
        """Only the download, list, install, update, uninstall, load, learn, and set-admin-password commands are exposed."""
        commands = {cmd.name for cmd in cli.commands.values()}
        assert commands == {
            "download",
            "list",
            "install",
            "update",
            "uninstall",
            "load",
            "learn",
            "set-admin-password",
        }


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

        result = self.runner.invoke(cli, ["list", "--installer-dir", "/test/installer", "--tree"])

        assert result.exit_code == 0
        assert "Tree output" in result.output
        mock_service.list_products.assert_called_once_with(as_tree=True, verbose=False)

    @patch("cli.commands.InstallerService")
    @patch("cli.commands.Path")
    def test_list_products_directory_not_exists(self, mock_path_class, mock_service_class) -> None:
        """Test product listing when directory doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        mock_service_class.return_value = MagicMock()

        result = self.runner.invoke(cli, ["list", "--installer-dir", "/nonexistent/installer"])

        assert result.exit_code == 0
        assert "Installer directory does not exist. No products installed." in result.output

    @patch("cli.commands.InstallerService")
    @patch("cli.commands.Path")
    def test_list_products_error_handling(self, mock_path_class, mock_service_class) -> None:
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

    @pytest.fixture(autouse=True)
    def _admin_account(self, monkeypatch):
        """Every install creates the 'admin' account: provide its password, mock the users load and DB update.

        Tests that check these steps patch them again with their own decorators, which take precedence.
        """
        monkeypatch.setenv("KBOT_ADMIN_PASSWORD", "K0nversOK!")
        with (
            patch("cli.commands.run_kbot_iam_load") as self.mock_run_kbot_iam_load,
            patch("cli.commands.set_admin_password") as self.mock_set_admin_password,
        ):
            yield

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
                "--installer-dir",
                str(installer_dir),
                "--workarea-dir",
                str(workarea_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        assert mock_build_downloadable.call_args.kwargs["include_dependencies"] is True
        mock_build_downloadable.return_value.download.assert_called_once_with(installer_dir)
        mock_build_workarea.assert_called_once_with(installer_path=installer_dir, workarea_path=workarea_dir)
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
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code != 0
        assert "Option '-v/--version' is required" in result.output

    @patch("cli.commands.build_downloadable")
    def test_install_aborts_when_workarea_already_exists(self, mock_build_downloadable, tmp_path) -> None:
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
    def test_install_force_recreate_deletes_existing_workarea(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--force-recreate deletes an existing workarea instead of cancelling."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()

        installer_dir = tmp_path / "installer"
        workarea_dir = tmp_path / "work"
        workarea_dir.mkdir()
        (workarea_dir / "stale_marker").write_text("leftover from a previous install", encoding="utf-8")
        _write_product(installer_dir, "jira")

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--installer-dir",
                str(installer_dir),
                "--workarea-dir",
                str(workarea_dir),
                "--force-recreate",
            ],
        )

        assert result.exit_code == 0, result.output
        assert not (workarea_dir / "stale_marker").exists()
        mock_build_downloadable.return_value.download.assert_called_once_with(installer_dir)
        mock_build_workarea.return_value.install.assert_called_once()
        mock_build_database.assert_called_once()

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_no_db_password_generates_random_db_password(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--no-db-password generates and displays a random database password."""
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
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
                "--no-db-password",
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
        monkeypatch,
    ) -> None:
        """Providing --db-host selects the external database backend.

        PG_DIR is still resolved (and passed through to build_database) even in
        external mode, since a ``psql`` client is needed to apply schema files
        regardless of where the database itself is hosted.
        """
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
        assert mock_build_database.call_args.kwargs["pg_dir"] == tmp_path / "pg"

    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_requires_pg_dir_env(
        self, mock_build_downloadable, mock_build_workarea, tmp_path, monkeypatch
    ) -> None:
        """Install fails when neither PG_DIR nor 3rdparty/versions.env is available.

        This applies regardless of database mode, since a ``psql`` client
        (resolved from PG_DIR) is required in every case to apply schema files.
        """
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
            "THIRDPARTY_PATH=${THIRDPARTY_HOME}\nPG_VERSION=11.5\nPG_DIR=${THIRDPARTY_PATH}/postgresql-${PG_VERSION}\n",
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
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
                "--skip-python-requirements",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_install_python_requirements.assert_not_called()

    @patch("cli.commands.set_admin_password")
    @patch("cli.commands.run_kbot_command")
    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_with_load_runs_kbot_load_and_sets_admin_password(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        mock_run_kbot_command,
        mock_set_admin_password,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--with-load runs 'kbot.sh load' and sets the admin password from the env var."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        monkeypatch.setenv("KBOT_ADMIN_PASSWORD", "K0nversOK!")
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()
        workarea_dir = tmp_path / "work"

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(workarea_dir),
                "--with-load",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_run_kbot_command.assert_called_once_with(workarea_dir, "load")
        self.mock_run_kbot_iam_load.assert_not_called()
        mock_set_admin_password.assert_called_once()
        assert mock_set_admin_password.call_args.args[1] == "K0nversOK!"

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_with_load_requires_admin_password(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--with-load without KBOT_ADMIN_PASSWORD or --no-admin-password fails before downloading."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        monkeypatch.delenv("KBOT_ADMIN_PASSWORD", raising=False)
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
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
                "--with-load",
            ],
        )

        assert result.exit_code != 0
        assert "KBOT_ADMIN_PASSWORD" in result.output
        mock_build_downloadable.assert_not_called()

    @patch("cli.commands.run_kbot_command")
    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_without_load_loads_users_and_sets_admin_password(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        mock_run_kbot_command,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Without --with-load, only the users are loaded ('core.sh load -p') so that 'admin' exists."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()
        workarea_dir = tmp_path / "work"

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(workarea_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        self.mock_run_kbot_iam_load.assert_called_once_with(workarea_dir)
        mock_run_kbot_command.assert_not_called()
        self.mock_set_admin_password.assert_called_once()
        assert self.mock_set_admin_password.call_args.args[1] == "K0nversOK!"

    @patch("cli.commands.build_downloadable")
    def test_install_without_load_requires_admin_password(self, mock_build_downloadable, tmp_path, monkeypatch) -> None:
        """Even without --with-load, a missing admin password fails before downloading."""
        monkeypatch.delenv("KBOT_ADMIN_PASSWORD", raising=False)

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code != 0
        assert "KBOT_ADMIN_PASSWORD" in result.output
        mock_build_downloadable.assert_not_called()

    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_fails_when_admin_account_is_missing(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        tmp_path,
        monkeypatch,
    ) -> None:
        """If the users load did not create 'admin', the install fails instead of reporting success."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()
        self.mock_set_admin_password.side_effect = RuntimeError("No 'admin' account found in the database")

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code != 0
        assert "No 'admin' account found" in result.output
        assert "Installation completed successfully." not in result.output

    @patch("cli.commands.set_admin_password")
    @patch("cli.commands.run_kbot_command")
    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_with_load_and_no_admin_password_generates_one(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        mock_run_kbot_command,
        mock_set_admin_password,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--no-admin-password generates and displays a random admin password."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        monkeypatch.delenv("KBOT_ADMIN_PASSWORD", raising=False)
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
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
                "--with-load",
                "--no-admin-password",
            ],
        )

        assert result.exit_code == 0, result.output
        generated_password = mock_set_admin_password.call_args.args[1]
        assert generated_password
        assert generated_password in result.output

    @patch("cli.commands.run_kbot_command")
    @patch("cli.commands.build_database")
    @patch("cli.commands.build_workarea")
    @patch("cli.commands.build_downloadable")
    def test_install_with_learn_runs_kbot_learn(
        self,
        mock_build_downloadable,
        mock_build_workarea,
        mock_build_database,
        mock_run_kbot_command,
        tmp_path,
        monkeypatch,
    ) -> None:
        """--with-learn runs 'kbot.sh learn' after installing."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        mock_build_downloadable.return_value = MagicMock()
        mock_build_workarea.return_value = MagicMock()
        workarea_dir = tmp_path / "work"

        result = self.runner.invoke(
            cli,
            [
                "install",
                "--product",
                "jira",
                "--version",
                "2025.03-dev",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(workarea_dir),
                "--with-learn",
            ],
        )

        assert result.exit_code == 0, result.output
        mock_run_kbot_command.assert_called_once_with(workarea_dir, "learn")


class TestUpdateCommand:
    """Test cases for the 'update' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.WorkareaUpdatable")
    @patch("cli.commands.build_workarea")
    def test_update_workarea_success(
        self,
        mock_build_workarea,
        mock_workarea_updatable,
        tmp_path,
    ) -> None:
        """--workarea builds the workarea and dispatches to WorkareaUpdatable with --how."""
        installer_dir = tmp_path / "installer"
        workarea_dir = tmp_path / "work"
        mock_build_workarea.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "update",
                "--workarea",
                "--how",
                "repair",
                "--installer-dir",
                str(installer_dir),
                "--workarea-dir",
                str(workarea_dir),
            ],
        )

        assert result.exit_code == 0, result.output
        mock_build_workarea.assert_called_once_with(installer_path=installer_dir, workarea_path=workarea_dir)
        assert mock_build_workarea.return_value.update_mode is True
        mock_workarea_updatable.assert_called_once_with(
            installable=mock_build_workarea.return_value,
            mode=UpdatableName.REPAIR,
        )
        mock_workarea_updatable.return_value.assert_called_once()

    @patch("cli.commands.WorkareaUpdatable")
    @patch("cli.commands.build_workarea")
    def test_update_workarea_defaults_how_to_smooth(
        self,
        mock_build_workarea,
        mock_workarea_updatable,
        tmp_path,
    ) -> None:
        """--how defaults to 'smooth' when not specified."""
        mock_build_workarea.return_value = MagicMock()

        result = self.runner.invoke(
            cli,
            [
                "update",
                "--workarea",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code == 0, result.output
        assert mock_workarea_updatable.call_args.kwargs["mode"] == UpdatableName.SMOOTH

    def test_update_requires_a_target(self, tmp_path) -> None:
        """Update fails when no target (--installer or --workarea) is specified."""
        result = self.runner.invoke(
            cli,
            [
                "update",
                "--installer-dir",
                str(tmp_path / "installer"),
                "--workarea-dir",
                str(tmp_path / "work"),
            ],
        )

        assert result.exit_code != 0
        assert "Nothing to update" in result.output

    @patch("cli.commands.install_product_python_requirements")
    @patch("cli.commands.WorkareaUpdatable")
    @patch("cli.commands.InstallerUpdatable")
    def test_update_installer_success(
        self,
        mock_installer_updatable,
        mock_workarea_updatable,
        mock_install_python_requirements,
        tmp_path,
    ) -> None:
        """--installer runs InstallerUpdatable with --storage/-V, without touching the workarea."""
        installer_dir = tmp_path / "installer"
        mock_installer_updatable.return_value.return_value = []

        result = self.runner.invoke(
            cli,
            ["update", "--installer", "--storage", "s3", "-V", "--installer-dir", str(installer_dir)],
        )

        assert result.exit_code == 0, result.output
        mock_installer_updatable.assert_called_once_with(
            installer_path=installer_dir,
            storage_backend=StorageBackendEnum.S3,
            verbose=True,
        )
        mock_installer_updatable.return_value.assert_called_once()
        mock_install_python_requirements.assert_called_once_with(installer_dir)
        mock_workarea_updatable.assert_not_called()
        assert "Update completed successfully." in result.output

    @patch("cli.commands.install_product_python_requirements")
    @patch("cli.commands.InstallerUpdatable")
    def test_update_installer_failures_exit_non_zero(
        self,
        mock_installer_updatable,
        mock_install_python_requirements,
        tmp_path,
    ) -> None:
        """Products that failed to update are listed and the command fails."""
        mock_installer_updatable.return_value.return_value = ["qakeys"]

        result = self.runner.invoke(
            cli,
            ["update", "--installer", "--installer-dir", str(tmp_path / "installer")],
        )

        assert result.exit_code != 0
        assert "Update finished with errors for: qakeys" in result.output
        mock_install_python_requirements.assert_called_once()


class TestLoadCommand:
    """Test cases for the 'load' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.run_kbot_command")
    def test_load_runs_kbot_load(self, mock_run_kbot_command, tmp_path) -> None:
        """'load' runs 'kbot.sh load' against the workarea directory."""
        workarea_dir = tmp_path / "work"

        result = self.runner.invoke(cli, ["load", "--workarea-dir", str(workarea_dir)])

        assert result.exit_code == 0, result.output
        mock_run_kbot_command.assert_called_once_with(workarea_dir, "load")

    @patch("cli.commands.run_kbot_command")
    def test_load_reports_error(self, mock_run_kbot_command, tmp_path) -> None:
        """A failing 'kbot.sh load' aborts with an error message."""
        mock_run_kbot_command.side_effect = RuntimeError("boom")

        result = self.runner.invoke(cli, ["load", "--workarea-dir", str(tmp_path / "work")])

        assert result.exit_code != 0
        assert "Error loading data" in result.output


class TestLearnCommand:
    """Test cases for the 'learn' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.run_kbot_command")
    def test_learn_runs_kbot_learn(self, mock_run_kbot_command, tmp_path) -> None:
        """'learn' runs 'kbot.sh learn' against the workarea directory."""
        workarea_dir = tmp_path / "work"

        result = self.runner.invoke(cli, ["learn", "--workarea-dir", str(workarea_dir)])

        assert result.exit_code == 0, result.output
        mock_run_kbot_command.assert_called_once_with(workarea_dir, "learn")

    @patch("cli.commands.run_kbot_command")
    def test_learn_reports_error(self, mock_run_kbot_command, tmp_path) -> None:
        """A failing 'kbot.sh learn' aborts with an error message."""
        mock_run_kbot_command.side_effect = RuntimeError("boom")

        result = self.runner.invoke(cli, ["learn", "--workarea-dir", str(tmp_path / "work")])

        assert result.exit_code != 0
        assert "Error learning models" in result.output


class TestSetAdminPasswordCommand:
    """Test cases for the 'set-admin-password' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cli.commands.set_admin_password")
    def test_setadminpassword_valid_uses_env_password_and_default_db_settings(
        self, mock_set_admin_password, tmp_path, monkeypatch
    ) -> None:
        """The admin password comes from KBOT_ADMIN_PASSWORD, the DB settings from the defaults."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        monkeypatch.setenv("KBOT_ADMIN_PASSWORD", "K0nversOK!")

        result = self.runner.invoke(cli, ["set-admin-password"])

        assert result.exit_code == 0, result.output
        settings, password = mock_set_admin_password.call_args.args
        assert password == "K0nversOK!"
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.user == "kbot_db_user"
        assert settings.password == "kbot_db_pwd"
        assert settings.database == "kbot_db"
        assert settings.psql_path == tmp_path / "pg" / "bin" / "psql"

    @patch("cli.commands.set_admin_password")
    def test_setadminpassword_valid_forwards_db_options(self, mock_set_admin_password, tmp_path, monkeypatch) -> None:
        """Explicit --db-* options are used to connect to the database."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        monkeypatch.setenv("KBOT_ADMIN_PASSWORD", "K0nversOK!")

        result = self.runner.invoke(
            cli,
            [
                "set-admin-password",
                "--db-host",
                "db.example.com",
                "--db-port",
                "6543",
                "--db-user",
                "custom_user",
                "--db-password",
                "custom_pwd",
                "--db-name",
                "custom_db",
            ],
        )

        assert result.exit_code == 0, result.output
        settings = mock_set_admin_password.call_args.args[0]
        assert settings.host == "db.example.com"
        assert settings.port == 6543
        assert settings.user == "custom_user"
        assert settings.password == "custom_pwd"
        assert settings.database == "custom_db"

    @patch("cli.commands.set_admin_password")
    def test_setadminpassword_valid_generates_password_with_no_admin_password(
        self, mock_set_admin_password, tmp_path, monkeypatch
    ) -> None:
        """--no-admin-password generates and displays a random admin password."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        monkeypatch.delenv("KBOT_ADMIN_PASSWORD", raising=False)

        result = self.runner.invoke(cli, ["set-admin-password", "--no-admin-password"])

        assert result.exit_code == 0, result.output
        generated_password = mock_set_admin_password.call_args.args[1]
        assert f"Generated kbot admin password: {generated_password}" in result.output

    @patch("cli.commands.set_admin_password")
    def test_setadminpassword_invalid_requires_admin_password(self, mock_set_admin_password, monkeypatch) -> None:
        """Without KBOT_ADMIN_PASSWORD or --no-admin-password, the command fails fast."""
        monkeypatch.delenv("KBOT_ADMIN_PASSWORD", raising=False)

        result = self.runner.invoke(cli, ["set-admin-password"])

        assert result.exit_code != 0
        assert "KBOT_ADMIN_PASSWORD" in result.output
        mock_set_admin_password.assert_not_called()

    @patch("cli.commands.set_admin_password")
    def test_setadminpassword_invalid_reports_db_error(self, mock_set_admin_password, tmp_path, monkeypatch) -> None:
        """A database error aborts with an error message."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        monkeypatch.setenv("KBOT_ADMIN_PASSWORD", "K0nversOK!")
        mock_set_admin_password.side_effect = RuntimeError("boom")

        result = self.runner.invoke(cli, ["set-admin-password"])

        assert result.exit_code != 0
        assert "Error setting admin password" in result.output


class TestUninstallCommand:
    """Test cases for the 'uninstall' command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @pytest.fixture(autouse=True)
    def _env(self, tmp_path, monkeypatch) -> None:
        """Point PG_DIR and HOME ('~', the default backup location) into tmp_path."""
        monkeypatch.setenv("PG_DIR", str(tmp_path / "pg"))
        (tmp_path / "home").mkdir()
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

    @staticmethod
    def _make_workarea(tmp_path: Path) -> Path:
        workarea_dir = tmp_path / "work"
        (workarea_dir / "products" / "kbot").mkdir(parents=True)
        return workarea_dir

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_backs_up_stops_destroys_and_removes_workarea_in_order(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """'--backup-file ~' backs up into '~', then stops kbot, destroys the database, and removes the workarea."""
        workarea_dir = self._make_workarea(tmp_path)
        mock_create_database.return_value.backup.return_value = True
        manager = MagicMock()
        manager.attach_mock(mock_create_database.return_value.backup, "backup")
        manager.attach_mock(mock_run_kbot_command, "run_kbot_command")
        manager.attach_mock(mock_create_database.return_value.destroy, "destroy")

        result = self.runner.invoke(
            cli, ["uninstall", "--workarea-dir", str(workarea_dir), "--backup-file", "~", "--yes"]
        )

        assert result.exit_code == 0, result.output
        mock_create_database.assert_called_once_with(
            db_host=None,
            db_port=5432,
            db_user="kbot_db_user",
            password="kbot_db_pwd",
            db_name="kbot_db",
            workarea_path=workarea_dir,
            pg_dir=tmp_path / "pg",
        )
        assert [c[0] for c in manager.mock_calls] == ["backup", "run_kbot_command", "destroy"]
        backup_path = mock_create_database.return_value.backup.call_args.args[0]
        assert backup_path.parent == (tmp_path / "home").resolve()
        assert re.fullmatch(r"dump_\d{8}_\d{6}\.sql", backup_path.name)
        mock_run_kbot_command.assert_called_once_with(workarea_dir, "stop")
        assert not workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_uses_explicit_backup_file(self, mock_run_kbot_command, mock_create_database, tmp_path) -> None:
        """--backup-file with a file path dumps into that exact file."""
        workarea_dir = self._make_workarea(tmp_path)
        backup_file = tmp_path / "backups" / "kbot.sql"

        result = self.runner.invoke(
            cli,
            ["uninstall", "--workarea-dir", str(workarea_dir), "--backup-file", str(backup_file), "--yes"],
        )

        assert result.exit_code == 0, result.output
        mock_create_database.return_value.backup.assert_called_once_with(backup_file.resolve())

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_without_backup_file_skips_dump(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """Without --backup-file, everything is removed without dumping the database."""
        workarea_dir = self._make_workarea(tmp_path)

        result = self.runner.invoke(cli, ["uninstall", "--workarea-dir", str(workarea_dir), "--yes"])

        assert result.exit_code == 0, result.output
        assert "will NOT be backed up" in result.output
        mock_create_database.return_value.backup.assert_not_called()
        mock_create_database.return_value.destroy.assert_called_once_with()
        assert not workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_rejects_backup_file_inside_workarea(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """A backup file inside the workarea (removed right after) is rejected before anything happens."""
        workarea_dir = self._make_workarea(tmp_path)

        result = self.runner.invoke(
            cli,
            ["uninstall", "--workarea-dir", str(workarea_dir), "--backup-file", str(workarea_dir), "--yes"],
        )

        assert result.exit_code != 0
        assert "must be outside the workarea" in result.output
        mock_create_database.assert_not_called()
        mock_run_kbot_command.assert_not_called()
        assert workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_continues_when_there_is_no_database_to_back_up(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """A workarea whose install failed before creating the database is still uninstalled."""
        workarea_dir = self._make_workarea(tmp_path)
        mock_create_database.return_value.backup.return_value = False

        result = self.runner.invoke(
            cli, ["uninstall", "--workarea-dir", str(workarea_dir), "--backup-file", "~", "--yes"]
        )

        assert result.exit_code == 0, result.output
        assert "no database found, nothing to back up" in result.output
        mock_create_database.return_value.destroy.assert_called_once_with()
        assert not workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_keeps_everything_when_backup_fails(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """If the backup fails, kbot is not stopped and nothing is removed."""
        workarea_dir = self._make_workarea(tmp_path)
        mock_create_database.return_value.backup.side_effect = RuntimeError("pg_dump failed")

        result = self.runner.invoke(
            cli, ["uninstall", "--workarea-dir", str(workarea_dir), "--backup-file", "~", "--yes"]
        )

        assert result.exit_code != 0
        assert "Error uninstalling workarea: pg_dump failed" in result.output
        mock_run_kbot_command.assert_not_called()
        mock_create_database.return_value.destroy.assert_not_called()
        assert workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_forwards_external_db_options(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """With --db-host, the external database settings are forwarded."""
        workarea_dir = self._make_workarea(tmp_path)

        result = self.runner.invoke(
            cli,
            [
                "uninstall",
                "--workarea-dir",
                str(workarea_dir),
                "--db-host",
                "db.example.com",
                "--db-password",
                "secret",
                "--yes",
            ],
        )

        assert result.exit_code == 0, result.output
        kwargs = mock_create_database.call_args.kwargs
        assert kwargs["db_host"] == "db.example.com"
        assert kwargs["password"] == "secret"

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_asks_for_confirmation_and_stops_when_declined(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """Without --yes, declining the confirmation leaves everything in place."""
        workarea_dir = self._make_workarea(tmp_path)

        result = self.runner.invoke(cli, ["uninstall", "--workarea-dir", str(workarea_dir)], input="n\n")

        assert result.exit_code != 0
        assert "Continue with uninstallation?" in result.output
        mock_create_database.assert_not_called()
        mock_run_kbot_command.assert_not_called()
        assert workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_proceeds_when_confirmed(self, mock_run_kbot_command, mock_create_database, tmp_path) -> None:
        """Without --yes, confirming the prompt runs the uninstallation."""
        workarea_dir = self._make_workarea(tmp_path)

        result = self.runner.invoke(cli, ["uninstall", "--workarea-dir", str(workarea_dir)], input="y\n")

        assert result.exit_code == 0, result.output
        mock_create_database.return_value.destroy.assert_called_once_with()
        assert not workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_rejects_non_workarea_directory(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """A directory without 'products/kbot' is never removed."""
        other_dir = tmp_path / "not-a-workarea"
        other_dir.mkdir()

        result = self.runner.invoke(cli, ["uninstall", "--workarea-dir", str(other_dir), "--yes"])

        assert result.exit_code != 0
        assert "is not a kbot workarea directory" in result.output
        mock_run_kbot_command.assert_not_called()
        mock_create_database.assert_not_called()
        assert other_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_continues_when_kbot_stop_fails(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """A failing 'kbot.sh stop' only warns: the database is still destroyed and the workarea removed."""
        workarea_dir = self._make_workarea(tmp_path)
        mock_run_kbot_command.side_effect = RuntimeError("stop failed")

        result = self.runner.invoke(cli, ["uninstall", "--workarea-dir", str(workarea_dir), "--yes"])

        assert result.exit_code == 0, result.output
        assert "Warning: stop failed" in result.output
        mock_create_database.return_value.destroy.assert_called_once_with()
        assert not workarea_dir.exists()

    @patch("cli.commands.create_database")
    @patch("cli.commands.run_kbot_command")
    def test_uninstall_keeps_workarea_when_db_destruction_fails(
        self, mock_run_kbot_command, mock_create_database, tmp_path
    ) -> None:
        """If the database can't be destroyed, the workarea is kept and the command aborts."""
        workarea_dir = self._make_workarea(tmp_path)
        mock_create_database.return_value.destroy.side_effect = RuntimeError("still running")

        result = self.runner.invoke(cli, ["uninstall", "--workarea-dir", str(workarea_dir), "--yes"])

        assert result.exit_code != 0
        assert "Error uninstalling workarea: still running" in result.output
        assert workarea_dir.exists()


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
        assert "update" in result.output

    def test_cli_short_help_option(self) -> None:
        """Test that -h is an alias for --help on the group and subcommands."""
        for args in (["-h"], ["download", "-h"]):
            short = self.runner.invoke(cli, args)
            long = self.runner.invoke(cli, [*args[:-1], "--help"])
            assert short.exit_code == 0
            assert short.output == long.output
            assert "-h, --help" in short.output

    def test_download_help(self) -> None:
        """Test download command help."""
        result = self.runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0
        assert "Download kbot products from a product version or a bundle descriptor" in result.output

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

    def test_update_help(self) -> None:
        """Test update command help."""
        result = self.runner.invoke(cli, ["update", "--help"])
        assert result.exit_code == 0
        assert "Update parts of an existing kbot installation" in result.output


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
        code_lines = [line for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        code = "\n".join(code_lines)
        assert "env.sh" not in code
        assert "source" not in code

    def test_wrapper_does_not_set_pythonpath(self) -> None:
        """The wrapper must not export or mutate PYTHONPATH."""
        content = self._install_sh().read_text(encoding="utf-8")
        code_lines = [line for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        code = "\n".join(code_lines)
        assert "PYTHONPATH" not in code
