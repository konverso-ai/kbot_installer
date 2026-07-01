"""Tests for BundleInstallable."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from installable.bundle_installable import BundleInstallable
from installer_support.installation_table import InstallationTable
from storage.base import StorageBase
from utils.bundle import Bundle


def _sample_bundle_json() -> dict:
    """Build a minimal bundle descriptor for tests."""
    return {
        "name": "release",
        "version": "2025.03",
        "created_by": "tester",
        "created_on": "2026-01-01",
        "created_from": "ci",
        "timestamp": "2026-01-01",
        "versions": [
            {
                "name": "kbot",
                "version": "2025.03",
                "build": {
                    "timestamp": "2026/01/01",
                    "branch": "release-2025.03",
                    "commit": "commit-kbot",
                },
                "parents": ["framework"],
            },
            {
                "name": "framework",
                "version": "2025.03",
                "build": {
                    "timestamp": "2026/01/01",
                    "branch": "release-2025.03",
                    "commit": "commit-framework",
                },
                "parents": [],
            },
        ],
    }


def _build_bundle_installable(
    temp_dir: str,
    bundle: Bundle | None = None,
) -> BundleInstallable:
    """Build a BundleInstallable for tests."""
    bundle = bundle or Bundle.from_json(_sample_bundle_json())
    return BundleInstallable(
        bundle=bundle,
        bundle_name="release",
        bundle_version="2025.03",
        top_product="kbot",
        installer_dir=Path(temp_dir),
        storage=MagicMock(spec=StorageBase),
        installation_table=InstallationTable(),
        storage_backend="nexus",
    )


class TestBundleInstallable:
    """Test cases for BundleInstallable."""

    def test_download_valid_with_dependencies(self) -> None:
        """Test bundle download delegates to recursive product installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installable = _build_bundle_installable(temp_dir)

            with (
                patch.object(
                    installable, "_download_products_recursively"
                ) as mock_recursive,
                patch("installable.bundle_installable.ensure_directory") as mock_ensure,
            ):
                installable.download(dependencies=True)

                mock_ensure.assert_called_once_with(installable.installer_dir)
                mock_recursive.assert_called_once_with(
                    "kbot",
                    include_dependencies=True,
                )

    def test_download_valid_without_dependencies(self) -> None:
        """Test bundle download can skip dependency recursion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installable = _build_bundle_installable(temp_dir)

            with (
                patch.object(
                    installable, "_download_products_recursively"
                ) as mock_recursive,
                patch("installable.bundle_installable.ensure_directory"),
            ):
                installable.download(dependencies=False)

                mock_recursive.assert_called_once_with(
                    "kbot",
                    include_dependencies=False,
                )

    def test_from_storage_invalid_missing_top_product(self) -> None:
        """Test bundle creation fails when the top product is absent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_storage = MagicMock(spec=StorageBase)
            mock_storage.get.return_value = Bundle.from_json(
                _sample_bundle_json()
            ).model_dump_json()

            with pytest.raises(ValueError, match="not found in bundle"):
                BundleInstallable.from_storage(
                    bundle_name="release",
                    bundle_version="2025.03",
                    top_product="missing-product",
                    installer_dir=temp_dir,
                    storage=mock_storage,
                    installation_table=InstallationTable(),
                    storage_backend="nexus",
                )

    def test_fetch_bundle_valid_uses_primary_key(self) -> None:
        """Test bundle fetch reads the primary storage key."""
        mock_storage = MagicMock(spec=StorageBase)
        mock_storage.get.side_effect = lambda key: (
            Bundle.from_json(_sample_bundle_json()).model_dump_json()
            if key == "release-2025.03.json"
            else None
        )

        bundle = BundleInstallable._fetch_bundle(mock_storage, "release", "2025.03")

        assert bundle.name == "release"
        mock_storage.get.assert_any_call("release-2025.03.json")

    def test_download_pinned_product_valid_writes_stamp(self) -> None:
        """Test pinned product download writes nexus.json and extracts archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Bundle.from_json(_sample_bundle_json())
            framework = next(
                product for product in bundle.versions if product.name == "framework"
            )
            mock_storage = MagicMock(spec=StorageBase)

            def _fake_download(_key: str, dest: str) -> None:
                (Path(dest) / "framework").mkdir(parents=True, exist_ok=True)

            mock_storage.download.side_effect = _fake_download
            installable = BundleInstallable(
                bundle=bundle,
                bundle_name="release",
                bundle_version="2025.03",
                top_product="kbot",
                installer_dir=Path(temp_dir),
                storage=mock_storage,
                installation_table=InstallationTable(),
                storage_backend="nexus",
            )

            installable._download_pinned_product(framework)

            mock_storage.download.assert_called_once_with(
                "release-2025.03/framework/framework_commit-framework.tar.gz",
                temp_dir,
            )
            stamp_path = Path(temp_dir) / "framework" / "nexus.json"
            assert stamp_path.exists()

    def test_download_products_recursively_valid_skips_cached(self) -> None:
        """Test recursive bundle download skips products already at pinned commit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            installable = _build_bundle_installable(temp_dir)
            framework_dir = Path(temp_dir) / "framework"
            framework_dir.mkdir(parents=True)
            (framework_dir / "description.xml").write_text(
                "<product name='framework'></product>",
                encoding="utf-8",
            )
            (framework_dir / "nexus.json").write_text(
                '{"build": {"commit": "commit-framework"}}',
                encoding="utf-8",
            )

            with patch.object(installable, "_download_pinned_product") as mock_download:
                installable._download_products_recursively(
                    "kbot",
                    include_dependencies=True,
                )

            mock_download.assert_called_once()
            assert mock_download.call_args[0][0].name == "kbot"
            skipped = [
                result
                for result in installable.installation_table.results
                if result.status == "skipped"
            ]
            assert any(result.product_name == "framework" for result in skipped)
