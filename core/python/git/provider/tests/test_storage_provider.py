"""Tests for storage_provider module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from git.provider.base import ProviderBase
from git.provider.config import DEFAULT_PROVIDERS_CONFIG
from git.provider.errors import ProviderError
from git.provider.storage_provider import StorageProvider


class TestStorageProvider:
    """Test cases for StorageProvider class."""

    def test_inherits_from_provider_base(self) -> None:
        """Test that StorageProvider inherits from ProviderBase."""
        assert issubclass(StorageProvider, ProviderBase)

    def test_nexus_backend_get_name(self) -> None:
        """Test get_name returns storage."""
        provider = StorageProvider()
        assert provider.get_name() == "storage"

    def test_build_object_key(self) -> None:
        """Test object key format."""
        key = StorageProvider._build_object_key("my-repo", "dev")
        assert key == "dev/my-repo/my-repo_latest.tar.gz"

    def test_build_object_key_defaults_to_master(self) -> None:
        """Test object key defaults branch to master."""
        key = StorageProvider._build_object_key("my-repo", None)
        assert key == "master/my-repo/my-repo_latest.tar.gz"

    def test_nexus_backend_clone_uses_download(self) -> None:
        """Test Nexus clone uses storage.download."""
        provider = StorageProvider()

        with patch.object(provider._storage, "download") as mock_download:
            provider.clone_and_checkout("/tmp/target", "dev", repository_name="my-repo")
            mock_download.assert_called_once_with(
                "dev/my-repo/my-repo_latest.tar.gz",
                str(Path("/tmp/target").parent),
            )
            assert provider.get_branch() == "dev"

    def test_nexus_backend_clone_handles_error(self) -> None:
        """Test Nexus clone wraps failures in ProviderError."""
        provider = StorageProvider()

        with patch.object(
            provider._storage,
            "download",
            side_effect=RuntimeError("download failed"),
        ):
            with pytest.raises(ProviderError, match="Failed to clone repository"):
                provider.clone_and_checkout("/tmp/target", "dev", repository_name="my-repo")

    def test_nexus_backend_check_remote_repository_exists(self) -> None:
        """Test existence check uses storage.exists when available."""
        provider = StorageProvider()

        with patch.object(provider._storage, "exists", return_value=True) as mock_exists:
            assert provider.check_remote_repository_exists("my-repo") is True
            mock_exists.assert_called_once_with(
                "master/my-repo/my-repo_latest.tar.gz"
            )

    def test_get_branch_returns_default_before_clone(self) -> None:
        """Test get_branch returns default branch before clone."""
        provider = StorageProvider()
        assert provider.get_branch() == "master"

    def test_s3_backend_clone_calls_download(self) -> None:
        """Test S3 clone invokes storage.download with the expected key."""
        config = DEFAULT_PROVIDERS_CONFIG.model_copy(deep=True)
        config.storage.backend = "s3"
        config.storage.s3.bucket_name = "test-bucket"

        with patch("git.provider.storage_provider.add_storage") as mock_storage:
            mock_bucket = MagicMock()
            mock_storage.return_value = mock_bucket
            provider = StorageProvider(config=config)

            provider.clone_and_checkout("/tmp/target", "master", repository_name="my-repo")
            mock_bucket.download.assert_called_once_with(
                "master/my-repo/my-repo_latest.tar.gz",
                str(Path("/tmp/target").parent),
            )
            mock_storage.assert_called_once_with(
                "s3",
                **config.storage.get_backend_kwargs(None),
            )

    def test_s3_check_remote_repository_exists(self) -> None:
        """Test S3 existence check uses storage get when exists is unavailable."""
        config = DEFAULT_PROVIDERS_CONFIG.model_copy(deep=True)
        config.storage.backend = "s3"
        config.storage.s3.bucket_name = "test-bucket"

        with patch("git.provider.storage_provider.add_storage") as mock_storage:
            mock_bucket = MagicMock()
            mock_bucket.get.return_value = "content"
            mock_storage.return_value = mock_bucket
            provider = StorageProvider(config=config)

            assert provider.check_remote_repository_exists("my-repo") is True
            mock_bucket.get.assert_called_once_with(
                "master/my-repo/my-repo_latest.tar.gz"
            )

    def test_nexus_check_remote_repository_exists_exception(self) -> None:
        """Test existence check returns False when storage raises."""
        provider = StorageProvider()

        with patch.object(
            provider._storage, "exists", side_effect=RuntimeError("check failed")
        ):
            assert provider.check_remote_repository_exists("my-repo") is False

    def test_nexus_clone_creates_target_directory(self) -> None:
        """Test clone creates the target parent directory."""
        provider = StorageProvider()

        with patch.object(provider._storage, "download"):
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / "my-repo"
                provider.clone_and_checkout(target, "main", repository_name="my-repo")
                assert target.parent.exists()
