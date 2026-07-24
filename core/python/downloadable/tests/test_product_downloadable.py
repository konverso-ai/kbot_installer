"""Tests for ProductDownloadable."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from downloadable.product_downloadable import ProductDownloadable
from git.provider.base import ProviderBase
from installer_support.installation_table import InstallationTable
from utils.product.build import Build
from utils.product.product import Product


def _make_product(name: str, *, branch: str = "main", commit: str = "") -> Product:
    return Product(name=name, build=Build(branch=branch, commit=commit))


def _write_description_xml(path: Path, product: Product) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "description.xml").write_text(
        f'<product name="{product.name}"/>', encoding="utf-8"
    )


class TestProductDownloadableWithoutDependencies:
    """Tests for downloading a single product with no dependency traversal."""

    def test_download_clones_missing_product(self, tmp_path: Path) -> None:
        """A missing product should be cloned via the provider."""
        product = _make_product("acme")
        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "github"

        def _clone(*, target_path: Path, **_kwargs: object) -> None:
            _write_description_xml(Path(target_path), product)

        provider.clone_and_checkout.side_effect = _clone

        downloadable = ProductDownloadable(
            product=product,
            provider=provider,
            table=InstallationTable(),
            include_dependencies=False,
        )
        downloadable.download(tmp_path)

        provider.clone_and_checkout.assert_called_once_with(
            target_path=tmp_path / "acme",
            branch="main",
            repository_name="acme",
            commit=None,
        )
        assert (tmp_path / "acme" / "description.xml").exists()

    def test_download_skips_when_already_present_and_unpinned(
        self, tmp_path: Path
    ) -> None:
        """An existing unpinned product should not be re-downloaded."""
        product = _make_product("acme")
        product_dir = tmp_path / "acme"
        _write_description_xml(product_dir, product)

        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "github"

        ProductDownloadable(
            product=product,
            provider=provider,
            table=InstallationTable(),
            include_dependencies=False,
        ).download(tmp_path)

        provider.clone_and_checkout.assert_not_called()

    def test_download_raises_without_build_metadata(self, tmp_path: Path) -> None:
        """A product without build metadata cannot be cloned."""
        product = Product(name="acme")
        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "github"

        with pytest.raises(ValueError, match="build information"):
            ProductDownloadable(
                product=product,
                provider=provider,
                table=InstallationTable(),
                include_dependencies=False,
            ).download(tmp_path)


class TestProductDownloadableCommitPinning:
    """Tests for pinned-commit cache behavior and propagation."""

    def test_download_passes_pinned_commit_to_provider(self, tmp_path: Path) -> None:
        """A pinned product should forward its commit to the provider."""
        product = _make_product("acme", commit="abc123")
        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "storage"

        def _clone(*, target_path: Path, **_kwargs: object) -> None:
            _write_description_xml(Path(target_path), product)

        provider.clone_and_checkout.side_effect = _clone

        ProductDownloadable(
            product=product,
            provider=provider,
            table=InstallationTable(),
            include_dependencies=False,
        ).download(tmp_path)

        provider.clone_and_checkout.assert_called_once_with(
            target_path=tmp_path / "acme",
            branch="main",
            repository_name="acme",
            commit="abc123",
        )

    def test_download_skips_when_pinned_commit_matches(self, tmp_path: Path) -> None:
        """A pinned product already at the recorded commit should be skipped."""
        product = _make_product("acme", commit="abc123")
        product_dir = tmp_path / "acme"
        _write_description_xml(product_dir, product)
        (product_dir / "description.json").write_text(
            json.dumps(product.to_json()), encoding="utf-8"
        )

        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "storage"

        ProductDownloadable(
            product=product,
            provider=provider,
            table=InstallationTable(),
            include_dependencies=False,
        ).download(tmp_path)

        provider.clone_and_checkout.assert_not_called()

    def test_download_redownloads_when_pinned_commit_differs(
        self, tmp_path: Path
    ) -> None:
        """A pinned product whose recorded commit differs should be re-downloaded."""
        old_product = _make_product("acme", commit="old-commit")
        new_product = _make_product("acme", commit="new-commit")
        product_dir = tmp_path / "acme"
        _write_description_xml(product_dir, old_product)
        (product_dir / "description.json").write_text(
            json.dumps(old_product.to_json()), encoding="utf-8"
        )

        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "storage"

        def _clone(*, target_path: Path, **_kwargs: object) -> None:
            _write_description_xml(Path(target_path), new_product)

        provider.clone_and_checkout.side_effect = _clone

        ProductDownloadable(
            product=new_product,
            provider=provider,
            table=InstallationTable(),
            include_dependencies=False,
        ).download(tmp_path)

        provider.clone_and_checkout.assert_called_once_with(
            target_path=product_dir,
            branch="main",
            repository_name="acme",
            commit="new-commit",
        )


class TestProductDownloadableWithDependencies:
    """Tests for BFS dependency traversal."""

    def test_download_traverses_parent_dependencies(self, tmp_path: Path) -> None:
        """Parent products declared in description.xml should also be downloaded."""
        child = _make_product("child")
        parent = _make_product("parent")

        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "github"

        def _clone(*, target_path: Path, repository_name: str, **_kwargs: object) -> None:
            product = child if repository_name == "child" else parent
            target = Path(target_path)
            target.mkdir(parents=True, exist_ok=True)
            xml = f'<product name="{product.name}">'
            if product.name == "child":
                xml += '<parents><parent name="parent"/></parents>'
            xml += "</product>"
            (target / "description.xml").write_text(xml, encoding="utf-8")

        provider.clone_and_checkout.side_effect = _clone

        ProductDownloadable(
            product=child,
            provider=provider,
            table=InstallationTable(),
            include_dependencies=True,
        ).download(tmp_path)

        assert (tmp_path / "child" / "description.xml").exists()
        assert (tmp_path / "parent" / "description.xml").exists()
        assert provider.clone_and_checkout.call_count == 2

    def test_download_raises_when_dependency_description_missing(
        self, tmp_path: Path
    ) -> None:
        """A dependency clone that doesn't produce description.xml should raise."""
        product = _make_product("acme")
        provider = MagicMock(spec=ProviderBase)
        provider.get_name.return_value = "github"
        provider.clone_and_checkout.side_effect = lambda **_kwargs: None

        with pytest.raises(ValueError, match="description.xml not found"):
            ProductDownloadable(
                product=product,
                provider=provider,
                table=InstallationTable(),
                include_dependencies=True,
            ).download(tmp_path)
