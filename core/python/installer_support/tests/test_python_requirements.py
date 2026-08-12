"""Tests for installer_support.python_requirements."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from installer_support.python_requirements import install_product_python_requirements


def _write_product(
    installer_dir: Path,
    name: str,
    *,
    type_: str = "solution",
    with_requirements: bool = True,
) -> None:
    """Create a product folder with a description.xml (and requirements.txt) under installer_dir."""
    product_dir = installer_dir / name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "description.xml").write_text(
        f'<product name="{name}" type="{type_}"/>',
        encoding="utf-8",
    )
    if with_requirements:
        (product_dir / "requirements.txt").write_text("some-package==1.0\n", encoding="utf-8")


def _write_pip3(installer_dir: Path) -> Path:
    pip3 = installer_dir / "kbot" / "bin" / "pip3.sh"
    pip3.parent.mkdir(parents=True, exist_ok=True)
    pip3.write_text("#!/bin/sh\n", encoding="utf-8")
    return pip3


class TestInstallProductPythonRequirements:
    """Tests for install_product_python_requirements."""

    def test_skips_when_pip3_missing(self, tmp_path: Path) -> None:
        """Without a downloaded kbot/bin/pip3.sh, the function returns without running pip."""
        with patch("installer_support.python_requirements.subprocess.run") as mock_run:
            install_product_python_requirements(tmp_path)

        mock_run.assert_not_called()

    def test_installs_requirements_for_solution_and_customer_products(self, tmp_path: Path) -> None:
        """requirements.txt is installed for 'solution'/'customer' products, via pip3.sh."""
        pip3 = _write_pip3(tmp_path)
        _write_product(tmp_path, "my-solution", type_="solution")
        _write_product(tmp_path, "my-customer", type_="customer")

        with patch(
            "installer_support.python_requirements.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as mock_run:
            install_product_python_requirements(tmp_path)

        assert mock_run.call_count == 2
        called_commands = [call.args[0] for call in mock_run.call_args_list]
        assert [
            str(pip3),
            "install",
            "-r",
            str(tmp_path / "my-solution" / "requirements.txt"),
            "--quiet",
            "--disable-pip-version-check",
        ] in called_commands
        assert [
            str(pip3),
            "install",
            "-r",
            str(tmp_path / "my-customer" / "requirements.txt"),
            "--quiet",
            "--disable-pip-version-check",
        ] in called_commands

    def test_skips_products_of_other_types(self, tmp_path: Path) -> None:
        """Products whose type is not solution/customer are left untouched."""
        _write_pip3(tmp_path)
        _write_product(tmp_path, "a-dependency", type_="dependency")

        with patch("installer_support.python_requirements.subprocess.run") as mock_run:
            install_product_python_requirements(tmp_path)

        mock_run.assert_not_called()

    def test_skips_products_without_requirements_file(self, tmp_path: Path) -> None:
        """A solution/customer product without requirements.txt is skipped."""
        _write_pip3(tmp_path)
        _write_product(tmp_path, "my-solution", type_="solution", with_requirements=False)

        with patch("installer_support.python_requirements.subprocess.run") as mock_run:
            install_product_python_requirements(tmp_path)

        mock_run.assert_not_called()

    def test_raises_when_pip_install_fails(self, tmp_path: Path) -> None:
        """A non-zero pip3.sh exit code raises a RuntimeError."""
        _write_pip3(tmp_path)
        _write_product(tmp_path, "my-solution", type_="solution")

        with (
            patch(
                "installer_support.python_requirements.subprocess.run",
                return_value=MagicMock(returncode=1),
            ),
            pytest.raises(RuntimeError, match="my-solution"),
        ):
            install_product_python_requirements(tmp_path)
