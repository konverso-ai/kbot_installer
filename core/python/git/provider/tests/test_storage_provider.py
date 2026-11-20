"""Tests for storage_provider module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.storage_provider import StorageProvider
from git.provider.utils import build_object_key


class TestStorageProvider:
    """Test cases for StorageProvider class."""

    def test_inherits_from_provider_base(self) -> None:
        """Test that StorageProvider inherits from ProviderBase."""
        assert issubclass(StorageProvider, ProviderBase)

    def test_nexus_backend_get_name(self) -> None:
        """Test get_name returns storage."""
        provider = StorageProvider(storage=MagicMock())
        assert provider.get_name() == "storage"

    def test_build_object_key(self) -> None:
        """Test object key format."""
        key = build_object_key("my-repo", "dev")
        assert key == "dev/my-repo/my-repo_latest.tar.gz"

    def test_build_object_key_defaults_to_master(self) -> None:
        """Test object key defaults branch to master."""
        key = build_object_key("my-repo", None)
        assert key == "master/my-repo/my-repo_latest.tar.gz"

    def test_nexus_backend_clone_uses_download(self) -> None:
        """Test Nexus clone uses storage.download."""
        provider = StorageProvider(storage=MagicMock())

        with patch.object(provider._storage, "download") as mock_download:
            provider.clone_and_checkout("my-repo", "/tmp/target", branch="dev")
            mock_download.assert_called_once_with(
                "dev/my-repo/my-repo_latest.tar.gz",
                str(Path("/tmp/target").parent),
            )
            assert provider.get_branch() == "dev"

    def test_nexus_backend_clone_handles_error(self) -> None:
        """Test Nexus clone wraps failures in ProviderError."""
        provider = StorageProvider(storage=MagicMock())

        with patch.object(
            provider._storage,
            "download",
            side_effect=RuntimeError("download failed"),
        ):
            with pytest.raises(ProviderError, match="Failed to clone repository"):
                provider.clone_and_checkout("my-repo", "/tmp/target", branch="dev")

    def test_get_latest_build_reads_description_next_to_latest_archive(self) -> None:
        """The latest build comes from description_latest.json, without downloading the archive."""
        storage = MagicMock()
        storage.get.return_value = '{"name": "my-repo", "build": {"branch": "dev", "commit": "abc123"}}'
        provider = StorageProvider(storage=storage)

        build = provider.get_latest_build("my-repo", "dev")

        storage.get.assert_called_once_with("dev/my-repo/description_latest.json")
        storage.download.assert_not_called()
        assert build is not None
        assert build.commit == "abc123"

    @pytest.mark.parametrize("content", [None, "not json"])
    def test_get_latest_build_unknown_when_description_missing_or_invalid(self, content: str | None) -> None:
        """A missing or unreadable description yields None, so callers fall back to downloading."""
        storage = MagicMock()
        storage.get.return_value = content

        assert StorageProvider(storage=storage).get_latest_build("my-repo", "dev") is None

    def test_get_latest_build_wraps_storage_errors(self) -> None:
        """A storage failure is reported as a ProviderError."""
        storage = MagicMock()
        storage.get.side_effect = RuntimeError("network down")

        with pytest.raises(ProviderError, match="network down"):
            StorageProvider(storage=storage).get_latest_build("my-repo", "dev")

    def test_nexus_backend_check_remote_repository_exists(self) -> None:
        """Test existence check uses storage.exists when available."""

        class _StorageWithExists:
            def exists(self, key: str) -> bool:
                raise NotImplementedError

        provider = StorageProvider(storage=_StorageWithExists())

        with patch.object(provider._storage, "exists", return_value=True) as mock_exists:
            assert provider.remote_exists("my-repo") is True
            mock_exists.assert_called_once_with(
                "master/my-repo/my-repo_latest.tar.gz"
            )

    def test_get_branch_returns_default_before_clone(self) -> None:
        """Test get_branch returns default branch before clone."""
        provider = StorageProvider(storage=MagicMock())
        assert provider.get_branch() == "master"

    def test_branches_defaults_to_empty_list(self) -> None:
        """Test that self.branches defaults to the class-level empty fallback list."""
        provider = StorageProvider(storage=MagicMock())
        assert provider.branches == []

    def test_branches_can_be_overridden(self) -> None:
        """Test that an explicit branches argument overrides the class default."""
        provider = StorageProvider(storage=MagicMock(), branches=["release", "stable"])
        assert provider.branches == ["release", "stable"]

    def test_s3_backend_clone_calls_download(self) -> None:
        """Test S3 clone invokes storage.download with the expected key."""
        mock_bucket = MagicMock()
        provider = StorageProvider(storage=mock_bucket)

        provider.clone_and_checkout("my-repo", "/tmp/target", branch="master")
        mock_bucket.download.assert_called_once_with(
            "master/my-repo/my-repo_latest.tar.gz",
            str(Path("/tmp/target").parent),
        )

    def test_s3_check_remote_repository_exists(self) -> None:
        """Test S3 existence check uses storage get when exists is unavailable."""
        mock_bucket = MagicMock(spec=["get"])
        mock_bucket.get.return_value = "content"
        provider = StorageProvider(storage=mock_bucket)

        assert provider.remote_exists("my-repo") is True
        mock_bucket.get.assert_called_once_with(
            "master/my-repo/my-repo_latest.tar.gz"
        )

    def test_nexus_check_remote_repository_exists_exception(self) -> None:
        """Test existence check returns False when storage raises."""

        class _StorageWithExists:
            def exists(self, key: str) -> bool:
                raise NotImplementedError

        provider = StorageProvider(storage=_StorageWithExists())

        with patch.object(
            provider._storage, "exists", side_effect=RuntimeError("check failed")
        ):
            assert provider.remote_exists("my-repo") is False

    def test_nexus_clone_creates_target_directory(self) -> None:
        """Test clone creates the target parent directory."""
        provider = StorageProvider(storage=MagicMock())

        with patch.object(provider._storage, "download"):
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / "my-repo"
                provider.clone_and_checkout("my-repo", target, branch="main")
                assert target.parent.exists()
