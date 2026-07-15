"""Tests for BundleDownloadable."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from downloadable.bundle_downloadable import BundleDownloadable
from storage.base import StorageBackend
from utils.bundle import Bundle
from utils.product.build import Build
from utils.product.product import Product


def _bundle_json(name: str = "acme-bundle", version: str = "1.0.0") -> dict:
    return {
        "name": name,
        "version": version,
        "versions": [
            {
                "@name": "child",
                "build": {"branch": "main", "commit": "child-commit"},
            },
            {
                "@name": "parent",
                "build": {"branch": "main", "commit": "parent-commit"},
            },
        ],
    }


@pytest.fixture
def mock_storages():
    """Patch add_storage to return distinct mocks for bundles/artifacts containers."""
    bundle_storage = MagicMock()
    artifact_storage = MagicMock()

    def _add_storage(*, name: str, container_name: str):  # noqa: ARG001
        return bundle_storage if container_name == "bundles" else artifact_storage

    with patch(
        "downloadable.bundle_downloadable.add_storage", side_effect=_add_storage
    ):
        yield bundle_storage, artifact_storage


@pytest.fixture
def mock_writer():
    """Patch add_writer to avoid touching the filesystem for the bundle cache file."""
    writer = MagicMock()
    with patch("downloadable.bundle_downloadable.add_writer", return_value=writer):
        yield writer


class TestBundleDownloadableInit:
    """Tests for bundle descriptor resolution."""

    def test_init_fetches_and_caches_bundle_descriptor(
        self, tmp_path: Path, mock_storages, mock_writer
    ) -> None:
        """The bundle descriptor should be fetched from the bundles container and cached."""
        bundle_storage, _artifact_storage = mock_storages
        bundle_storage.get.return_value = json.dumps(_bundle_json())

        downloadable = BundleDownloadable(
            storage_name=StorageBackend.S3,
            name="acme-bundle",
            installer_dir=tmp_path,
        )

        bundle_storage.get.assert_called_once_with(
            str(Bundle.file_name("acme-bundle"))
        )
        mock_writer.write.assert_called_once()
        assert downloadable is not None

    def test_init_raises_when_bundle_not_found(
        self, tmp_path: Path, mock_storages, mock_writer
    ) -> None:
        """A missing bundle descriptor should raise ValueError."""
        bundle_storage, _artifact_storage = mock_storages
        bundle_storage.get.return_value = None

        with pytest.raises(ValueError, match="was not found"):
            BundleDownloadable(
                storage_name=StorageBackend.S3,
                name="acme-bundle",
                installer_dir=tmp_path,
            )


class TestBundleDownloadableDownload:
    """Tests for downloading every product declared by the bundle."""

    def test_download_creates_one_product_downloadable_per_product(
        self, tmp_path: Path, mock_storages, mock_writer
    ) -> None:
        """Each product in the bundle should be downloaded via ProductDownloadable."""
        bundle_storage, _artifact_storage = mock_storages
        bundle_storage.get.return_value = json.dumps(_bundle_json())

        downloadable = BundleDownloadable(
            storage_name=StorageBackend.S3,
            name="acme-bundle",
            installer_dir=tmp_path,
        )

        with patch(
            "downloadable.bundle_downloadable.ProductDownloadable"
        ) as mock_product_downloadable_cls:
            mock_instance = MagicMock()
            mock_product_downloadable_cls.return_value = mock_instance

            downloadable.download(tmp_path)

            assert mock_product_downloadable_cls.call_count == 2
            downloaded_names = {
                call.kwargs["product"].name
                for call in mock_product_downloadable_cls.call_args_list
            }
            assert downloaded_names == {"child", "parent"}
            for call in mock_product_downloadable_cls.call_args_list:
                assert call.kwargs["include_dependencies"] is False
            assert mock_instance.download.call_count == 2

    def test_download_uses_storage_provider_for_pinned_commits(
        self, tmp_path: Path, mock_storages, mock_writer
    ) -> None:
        """Bundle products should be downloaded through a StorageProvider that
        supports commit pinning, targeting the artifact storage container.
        """
        bundle_storage, artifact_storage = mock_storages
        bundle_storage.get.return_value = json.dumps(_bundle_json())

        with patch(
            "downloadable.bundle_downloadable.StorageProvider"
        ) as mock_storage_provider_cls:
            mock_provider = MagicMock()
            mock_storage_provider_cls.return_value = mock_provider

            downloadable = BundleDownloadable(
                storage_name=StorageBackend.S3,
                name="acme-bundle",
                installer_dir=tmp_path,
            )

            mock_storage_provider_cls.assert_called_once_with(
                storage=artifact_storage
            )

            with patch(
                "downloadable.bundle_downloadable.ProductDownloadable"
            ) as mock_product_downloadable_cls:
                downloadable.download(tmp_path)

                for call in mock_product_downloadable_cls.call_args_list:
                    assert call.kwargs["provider"] is mock_provider
