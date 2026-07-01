"""Tests for Product install, pyproject_path, and get_kconf methods."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from installable import create_installable
from installable.product_collection import ProductCollection
from installable.product_installable import ProductInstallable


def _prepare_installer_product(
    temp_dir: Path, product_name: str, source_dir: Path
) -> Path:
    """Create installer directory layout for install() tests."""
    installer_dir = Path(temp_dir) / "installer"
    installer_product_dir = installer_dir / product_name
    installer_product_dir.mkdir(parents=True)
    for item in source_dir.iterdir():
        destination = installer_product_dir / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)
    (installer_product_dir / "description.xml").write_text(
        f'<product name="{product_name}"/>'
    )
    return installer_dir


class TestProductInstall:
    """Test cases for Product install, pyproject_path, and get_kconf methods."""

    def test_pyproject_path_success(self) -> None:
        """Test pyproject_path property when file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            product = create_installable(name="test-product")
            product.dirname = product_dir

            # Create pyproject.toml
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text('[project]\nname = "test-product"\n')

            assert product.pyproject_path == pyproject_file
            assert product.pyproject_path.exists()

    def test_pyproject_path_no_dirname(self) -> None:
        """Test pyproject_path property when dirname is not set."""
        product = create_installable(name="test-product")
        product.dirname = None

        with pytest.raises(FileNotFoundError, match="has no dirname set"):
            _ = product.pyproject_path

    def test_pyproject_path_file_not_found(self) -> None:
        """Test pyproject_path property when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            product = create_installable(name="test-product")
            product.dirname = product_dir

            with pytest.raises(FileNotFoundError, match=r"pyproject\.toml not found"):
                _ = product.pyproject_path

    def test_get_kconf_single_product(self) -> None:
        """Test get_kconf with single product."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            conf_dir = product_dir / "conf"
            conf_dir.mkdir()

            # Create kbot.conf
            conf_file = conf_dir / "kbot.conf"
            conf_file.write_text(
                "[database]\nhost = localhost\nport = 5432\n\n[app]\nname = test\n"
            )

            product = create_installable(name="test-product")
            product.dirname = product_dir

            with patch.object(
                ProductInstallable,
                "get_dependencies",
                return_value=ProductCollection([product]),
            ):
                result = product.get_kconf()

            assert "aggregated" in result
            assert "test-product" in result
            assert result["test-product"]["database"]["host"] == "localhost"
            assert result["test-product"]["database"]["port"] == "5432"
            assert result["aggregated"]["database"]["host"] == "localhost"

    def test_get_kconf_multiple_products(self) -> None:
        """Test get_kconf with multiple products (BFS order)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create product1
            product1_dir = Path(temp_dir) / "product1"
            product1_dir.mkdir()
            conf1_dir = product1_dir / "conf"
            conf1_dir.mkdir()
            conf1_file = conf1_dir / "kbot.conf"
            conf1_file.write_text(
                "[database]\nhost = db1\nport = 5432\n\n[app]\nname = product1\n"
            )

            # Create product2 (depends on product1)
            product2_dir = Path(temp_dir) / "product2"
            product2_dir.mkdir()
            conf2_dir = product2_dir / "conf"
            conf2_dir.mkdir()
            conf2_file = conf2_dir / "kbot.conf"
            conf2_file.write_text(
                "[database]\nhost = db2\n\n[logging]\nlevel = debug\n"
            )

            product1 = create_installable(name="product1")
            product1.dirname = product1_dir

            product2 = create_installable(name="product2", parents=["product1"])
            product2.dirname = product2_dir

            with patch.object(
                ProductInstallable,
                "get_dependencies",
                return_value=ProductCollection([product1, product2]),
            ):
                result = product2.get_kconf()

            assert "aggregated" in result
            assert "product1" in result
            assert "product2" in result

            # Aggregated should have product2's values (last wins in BFS)
            assert result["aggregated"]["database"]["host"] == "db2"
            assert result["aggregated"]["database"]["port"] == "5432"  # From product1
            assert result["aggregated"]["app"]["name"] == "product1"
            assert result["aggregated"]["logging"]["level"] == "debug"

            # Individual configs
            assert result["product1"]["database"]["host"] == "db1"
            assert result["product2"]["database"]["host"] == "db2"

    def test_get_kconf_missing_file(self) -> None:
        """Test get_kconf when conf/kbot.conf doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            product = create_installable(name="test-product")
            product.dirname = product_dir

            with patch.object(
                ProductInstallable,
                "get_dependencies",
                return_value=ProductCollection([product]),
            ):
                result = product.get_kconf()

            assert "aggregated" in result
            assert "test-product" in result
            assert result["test-product"] == {}

    def test_get_kconf_specific_product(self) -> None:
        """Test get_kconf with specific product parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product1_dir = Path(temp_dir) / "product1"
            product1_dir.mkdir()
            conf1_dir = product1_dir / "conf"
            conf1_dir.mkdir()
            conf1_file = conf1_dir / "kbot.conf"
            conf1_file.write_text("[app]\nname = product1\n")

            product2_dir = Path(temp_dir) / "product2"
            product2_dir.mkdir()

            product1 = create_installable(name="product1")
            product1.dirname = product1_dir

            product2 = create_installable(name="product2", parents=["product1"])
            product2.dirname = product2_dir

            with patch.object(
                ProductInstallable,
                "get_dependencies",
                return_value=ProductCollection([product2, product1]),
            ):
                result = product2.get_kconf("product1")

            assert "product1" in result
            assert result["product1"]["app"]["name"] == "product1"

    def test_get_kconf_invalid_product(self) -> None:
        """Test get_kconf with invalid product name."""
        product = create_installable(name="test-product")

        with patch.object(
            ProductInstallable,
            "get_dependencies",
            return_value=ProductCollection([product]),
        ):
            with pytest.raises(ValueError, match="not found in dependencies"):
                product.get_kconf("invalid-product")

    def test_install_work_init(self) -> None:
        """Test install with work.init section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            # Create pyproject.toml with work.init
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_content = """[work.init]
var = ["pkl", "storage"]
logs = ["httpd"]
"""
            pyproject_file.write_text(pyproject_content)

            workarea = Path(temp_dir) / "workarea"
            product = create_installable(name="test-product")
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            product.install(workarea, dependencies=False, installer_path=installer_dir)

            # Check directories were created
            assert (workarea / "var" / "pkl").exists()
            assert (workarea / "var" / "storage").exists()
            assert (workarea / "logs" / "httpd").exists()

    def test_install_work_copy(self) -> None:
        """Test install with work.copy section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            core_dir = product_dir / "core"
            core_dir.mkdir()

            # Create source files
            (core_dir / "RunBot.py").write_text("print('run')")
            (core_dir / "Learn.py").write_text("print('learn')")

            # Create pyproject.toml with work.copy
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text(
                """[work.copy]
core = ["RunBot.py", "Learn.py"]
"""
            )

            workarea = Path(temp_dir) / "workarea"
            product = create_installable(name="test-product")
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            product.install(workarea, dependencies=False, installer_path=installer_dir)

            # Check files were copied
            assert (workarea / "core" / "RunBot.py").exists()
            assert (workarea / "core" / "Learn.py").exists()
            assert (workarea / "core" / "RunBot.py").read_text() == "print('run')"
            # Check it's a copy, not a symlink
            assert not (workarea / "core" / "RunBot.py").is_symlink()

    def test_install_work_link(self) -> None:
        """Test install with work.link section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            core_python_dir = product_dir / "core" / "python"
            core_python_dir.mkdir(parents=True)

            # Create source files
            (core_python_dir / "file1.py").write_text("print('file1')")
            (core_python_dir / "file2.py").write_text("print('file2')")

            # Create pyproject.toml with work.link
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text(
                """[work.link]
"core/python" = ["*.py"]
"""
            )

            workarea = Path(temp_dir) / "workarea"
            product = create_installable(name="test-product")
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            product.install(workarea, dependencies=False, installer_path=installer_dir)

            # Check symlinks were created
            link1 = workarea / "core" / "python" / "file1.py"
            link2 = workarea / "core" / "python" / "file2.py"

            assert link1.is_symlink()
            assert link2.is_symlink()
            # Symlink should point to installer directory, not product_dir
            installer_core_python_dir = (
                installer_dir / "test-product" / "core" / "python"
            )
            assert link1.readlink().samefile(installer_core_python_dir / "file1.py")

    def test_install_work_link_external(self) -> None:
        """Test install with work.link.external section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock site-packages
            site_packages = Path(temp_dir) / "site-packages"
            site_packages.mkdir()
            package_dir = site_packages / "drf_yasg"
            package_dir.mkdir()
            static_dir = package_dir / "static"
            static_dir.mkdir()
            (static_dir / "file.css").write_text("css content")

            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            # Create pyproject.toml with work.link.external
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text(
                """[work.link.external]
"drf_yasg/static" = "ui/web/static"
"""
            )

            workarea = Path(temp_dir) / "workarea"
            product = create_installable(name="test-product")
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            with patch("site.getsitepackages", return_value=[str(site_packages)]):
                product.install(
                    workarea, dependencies=False, installer_path=installer_dir
                )

            # Check symlink was created
            link = workarea / "ui" / "web" / "static"
            assert link.is_symlink()
            assert link.readlink().samefile(static_dir)

    def test_install_first_come_first_served(self) -> None:  # noqa: PLR0915
        """Test install with conflict resolution - first come first served."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Product1 (dependency, processed first)
            product1_dir = Path(temp_dir) / "product1"
            product1_dir.mkdir()
            core1_dir = product1_dir / "core" / "python"
            core1_dir.mkdir(parents=True)
            (core1_dir / "file.py").write_text("product1 content")

            pyproject1_file = product1_dir / "pyproject.toml"
            pyproject1_file.write_text(
                """[work.link]
"core/python" = ["file.py"]
"""
            )

            # Product2 (root, processed after)
            product2_dir = Path(temp_dir) / "product2"
            product2_dir.mkdir()
            core2_dir = product2_dir / "core" / "python"
            core2_dir.mkdir(parents=True)
            (core2_dir / "file.py").write_text("product2 content")

            pyproject2_file = product2_dir / "pyproject.toml"
            pyproject2_file.write_text(
                """[work.link]
"core/python" = ["file.py"]
"""
            )

            product1 = create_installable(name="product1")
            product2 = create_installable(name="product2", parents=["product1"])

            installer_dir = _prepare_installer_product(
                Path(temp_dir), "product1", product1_dir
            )
            _prepare_installer_product(Path(temp_dir), "product2", product2_dir)
            (installer_dir / "product2" / "description.xml").write_text(
                '<product name="product2"><parents><parent name="product1"/></parents></product>'
            )

            loaded_product1 = create_installable(name="product1")
            loaded_product1.load_from_installer_folder(installer_dir / "product1")
            loaded_product2 = create_installable(name="product2", parents=["product1"])
            loaded_product2.load_from_installer_folder(installer_dir / "product2")

            workarea = Path(temp_dir) / "workarea"
            with patch.object(
                ProductInstallable,
                "get_dependencies",
                return_value=ProductCollection([loaded_product1, loaded_product2]),
            ):
                product2.install(
                    workarea, dependencies=True, installer_path=installer_dir
                )

            # Check that product1's file won (first processed)
            link = workarea / "core" / "python" / "file.py"
            assert link.is_symlink()
            installer_core1_dir = installer_dir / "product1" / "core" / "python"
            assert link.read_text() == "product1 content"

    def test_install_work_ignore(self) -> None:
        """Test install with work.ignore patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            ui_dir = product_dir / "ui"
            ui_dir.mkdir()

            # Create files, some should be ignored
            (ui_dir / "static").mkdir()
            (ui_dir / "static" / "file.css").write_text("css")
            (ui_dir / "widget").mkdir()
            (ui_dir / "widget" / "file.js").write_text("js")

            # Create pyproject.toml with work.link and work.ignore
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text(
                """[work.link]
ui = ["*"]

[work.ignore]
ui = ["static"]
"""
            )

            workarea = Path(temp_dir) / "workarea"
            product = create_installable(name="test-product")
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            product.install(workarea, dependencies=False, installer_path=installer_dir)

            # Check that ignored directory is not linked
            assert not (workarea / "ui" / "static").exists()
            # But non-ignored directory is linked
            assert (workarea / "ui" / "widget").exists()

    def test_install_empty_patterns_link_everything(self) -> None:
        """Test install with empty patterns links everything."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            bin_dir = product_dir / "bin"
            bin_dir.mkdir()

            (bin_dir / "script1.sh").write_text("script1")
            (bin_dir / "script2.sh").write_text("script2")

            # Create pyproject.toml with empty patterns
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text(
                """[work.link]
bin = []
"""
            )

            workarea = Path(temp_dir) / "workarea"
            product = create_installable(name="test-product")
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            product.install(workarea, dependencies=False, installer_path=installer_dir)

            # Check directory is linked
            assert (workarea / "bin").exists()
            assert (workarea / "bin").is_symlink()

    def test_install_missing_pyproject_skipped(self) -> None:
        """Test install skips products without pyproject.toml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            workarea = Path(temp_dir) / "workarea"
            create_installable(name="test-product")
            installer_dir = Path(temp_dir) / "installer"
            installer_product_dir = installer_dir / "test-product"
            installer_product_dir.mkdir(parents=True)
            (installer_product_dir / "description.xml").write_text(
                '<product name="test-product"/>'
            )

            # Should not raise error, just skip
            create_installable(name="test-product").install(
                workarea, dependencies=False, installer_path=installer_dir
            )

            # Workarea should exist but be empty
            assert workarea.exists()

    def test_install_missing_work_section_skipped(self) -> None:
        """Test install skips products without work section."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()

            # Create pyproject.toml without work section
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text('[project]\nname = "test-product"\n')

            workarea = Path(temp_dir) / "workarea"
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            # Should not raise error, just skip
            create_installable(name="test-product").install(
                workarea, dependencies=False, installer_path=installer_dir
            )

            # Workarea should exist but be empty
            assert workarea.exists()

    def test_install_all_sections_together(self) -> None:
        """Test install with all work sections together."""
        with tempfile.TemporaryDirectory() as temp_dir:
            product_dir = Path(temp_dir) / "test-product"
            product_dir.mkdir()
            core_dir = product_dir / "core"
            core_dir.mkdir()
            python_dir = core_dir / "python"
            python_dir.mkdir()
            bin_dir = product_dir / "bin"
            bin_dir.mkdir()

            # Create source files
            (python_dir / "module.py").write_text("module")
            (core_dir / "RunBot.py").write_text("run")
            (bin_dir / "script.sh").write_text("script")

            # Create comprehensive pyproject.toml
            pyproject_file = product_dir / "pyproject.toml"
            pyproject_file.write_text(
                """[work.init]
var = ["pkl"]

[work.copy]
core = ["RunBot.py"]

[work.link]
"core/python" = ["*.py"]

[work.ignore]
bin = ["*.sh"]
"""
            )

            workarea = Path(temp_dir) / "workarea"
            product = create_installable(name="test-product")
            installer_dir = _prepare_installer_product(
                Path(temp_dir), "test-product", product_dir
            )

            product.install(workarea, dependencies=False, installer_path=installer_dir)

            # Check init
            assert (workarea / "var" / "pkl").exists()

            # Check copy
            assert (workarea / "core" / "RunBot.py").exists()
            assert not (workarea / "core" / "RunBot.py").is_symlink()
            assert (workarea / "core" / "RunBot.py").read_text() == "run"

            # Check link
            assert (workarea / "core" / "python" / "module.py").is_symlink()
