"""Tests for the downloadable factory module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from downloadable.base import DownloadableBase
from downloadable.factory import add_downloadable, build_downloadable
from storage.base import StorageBackendEnum


class TestAddDownloadable:
    """Test cases for add_downloadable function."""

    def test_add_downloadable_delegates_to_factory(self) -> None:
        """add_downloadable should delegate to factory_method with the package name."""
        with patch("downloadable.factory.factory_method") as mock_factory_method:
            mock_downloadable = MagicMock(spec=DownloadableBase)
            mock_factory_method.return_value = mock_downloadable

            result = add_downloadable("product", foo="bar")

            mock_factory_method.assert_called_once_with(
                name="product",
                package="downloadable",
                foo="bar",
            )
            assert result is mock_downloadable


class TestBuildDownloadable:
    """Test cases for build_downloadable function."""

    def test_build_downloadable_bundle_mode_returns_bundle_downloadable(
        self, tmp_path: Path
    ) -> None:
        """When bundle is set, a BundleDownloadable is returned, wired with storage/name/dir."""
        with patch("downloadable.factory.BundleDownloadable") as mock_bundle_cls:
            mock_bundle = MagicMock(spec=DownloadableBase)
            mock_bundle_cls.return_value = mock_bundle

            result = build_downloadable(
                product="kbot",
                version=None,
                bundle="ev-basic-2025.03.0016",
                installer_path=tmp_path,
                storage_backend=StorageBackendEnum.NEXUS,
                include_dependencies=True,
                verbose=True,
            )

            mock_bundle_cls.assert_called_once_with(
                storage_name=StorageBackendEnum.NEXUS,
                name="ev-basic-2025.03.0016",
                installer_dir=tmp_path,
                verbose=True,
            )
            assert result is mock_bundle

    def test_build_downloadable_product_mode_requires_version(self, tmp_path: Path) -> None:
        """Without a bundle, a missing version raises ValueError."""
        with pytest.raises(ValueError, match="version"):
            build_downloadable(
                product="jira",
                version=None,
                bundle=None,
                installer_path=tmp_path,
                storage_backend=StorageBackendEnum.NEXUS,
                include_dependencies=True,
            )

    def test_build_downloadable_product_mode_uses_default_providers(self, tmp_path: Path) -> None:
        """With no explicit provider, the default storage/github/bitbucket order is used."""
        with (
            patch("downloadable.factory.add_selector_provider") as mock_selector,
            patch("downloadable.factory.ProductDownloadable") as mock_product_cls,
        ):
            mock_product = MagicMock(spec=DownloadableBase)
            mock_product_cls.return_value = mock_product

            result = build_downloadable(
                product="jira",
                version="2025.03-dev",
                bundle=None,
                installer_path=tmp_path,
                storage_backend=StorageBackendEnum.NEXUS,
                include_dependencies=False,
            )

            mock_selector.assert_called_once_with(provider_names=["storage", "github", "bitbucket"])
            _, kwargs = mock_product_cls.call_args
            assert kwargs["product"].name == "jira"
            assert kwargs["include_dependencies"] is False
            assert result is mock_product

    def test_build_downloadable_product_mode_uses_explicit_providers(self, tmp_path: Path) -> None:
        """Explicitly requested providers are forwarded to the selector, in order."""
        with (
            patch("downloadable.factory.add_selector_provider") as mock_selector,
            patch("downloadable.factory.ProductDownloadable"),
        ):
            build_downloadable(
                product="jira",
                version="2025.03-dev",
                bundle=None,
                installer_path=tmp_path,
                provider=("github", "bitbucket"),
                storage_backend=StorageBackendEnum.NEXUS,
                include_dependencies=True,
            )

            mock_selector.assert_called_once_with(provider_names=["github", "bitbucket"])
