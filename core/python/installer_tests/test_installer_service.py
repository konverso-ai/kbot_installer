"""Tests for InstallerService."""

from pathlib import Path

from installer_support.installation_table import InstallationTable
from installer_support.installer_service import InstallerService


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


class TestInstallerServiceInit:
    """Tests for InstallerService construction."""

    def test_init_defaults(self, tmp_path: Path) -> None:
        """The service stores the installer directory and an installation table."""
        service = InstallerService(tmp_path)
        assert service.installer_dir == tmp_path
        assert service.verbose is False
        assert isinstance(service.get_installation_table(), InstallationTable)


class TestListProducts:
    """Tests for list_products / _load_products_from_disk."""

    def test_no_products_when_directory_missing(self, tmp_path: Path) -> None:
        """Listing a directory without products returns a friendly message."""
        service = InstallerService(tmp_path / "does-not-exist")
        assert service.list_products() == "No products installed."

    def test_no_products_when_directory_empty(self, tmp_path: Path) -> None:
        """An empty installer directory lists no products."""
        service = InstallerService(tmp_path)
        assert service.list_products() == "No products installed."

    def test_list_products_flat(self, tmp_path: Path) -> None:
        """Products with description.xml are listed with their dependencies."""
        _write_product(tmp_path, "child")
        _write_product(tmp_path, "parent", type_="framework", parents=["child"])

        output = InstallerService(tmp_path).list_products()

        assert "Installed products:" in output
        assert "- child (solution)" in output
        assert "- parent (framework)" in output
        assert "Dependencies: child" in output

    def test_list_products_ignores_folders_without_description(
        self, tmp_path: Path
    ) -> None:
        """Directories without a description.xml are skipped."""
        _write_product(tmp_path, "real")
        (tmp_path / "not-a-product").mkdir()

        output = InstallerService(tmp_path).list_products()

        assert "- real (solution)" in output
        assert "not-a-product" not in output

    def test_list_products_as_tree(self, tmp_path: Path) -> None:
        """Tree rendering shows the dependency hierarchy."""
        _write_product(tmp_path, "child")
        _write_product(tmp_path, "parent", parents=["child"])

        output = InstallerService(tmp_path).list_products(as_tree=True)

        assert "parent" in output
        assert "child" in output
        assert "└──" in output or "├──" in output

    def test_load_products_from_disk_merges_json(self, tmp_path: Path) -> None:
        """A sibling description.json is merged into the product."""
        _write_product(tmp_path, "prod")
        # description.json without a name is merged onto the XML product.
        (tmp_path / "prod" / "description.json").write_text(
            '{"name": "prod", "type": "customer"}', encoding="utf-8"
        )

        products = InstallerService(tmp_path)._load_products_from_disk()

        assert len(products) == 1
        assert products[0].name == "prod"
