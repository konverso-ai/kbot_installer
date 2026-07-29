"""Tests for provider/storage configuration models."""

from unittest.mock import MagicMock, patch

from git.provider.config import (
    AzureStorageSettings,
    NexusStorageSettings,
    OciStorageSettings,
    S3StorageSettings,
    StorageSectionConfig,
)


class TestNexusStorageSettingsBuildStorage:
    """Test cases for NexusStorageSettings.build_storage."""

    def test_uses_area_as_repository(self) -> None:
        """The area overrides the configured repository."""
        settings = NexusStorageSettings(domain="nexus.example.com", repository="raw")
        auth = MagicMock()

        with patch("git.provider.config.add_storage") as mock_add_storage:
            settings.build_storage("bundles", auth)

        mock_add_storage.assert_called_once_with(
            "nexus", domain="nexus.example.com", repository="bundles", auth=auth
        )

    def test_falls_back_to_configured_repository(self) -> None:
        """Without an area, the configured repository is used."""
        settings = NexusStorageSettings(domain="nexus.example.com", repository="raw")

        with patch("git.provider.config.add_storage") as mock_add_storage:
            settings.build_storage()

        mock_add_storage.assert_called_once_with(
            "nexus", domain="nexus.example.com", repository="raw", auth=None
        )


class TestS3StorageSettingsBuildStorage:
    """Test cases for S3StorageSettings.build_storage."""

    def test_uses_area_as_bucket_and_builds_backend(self) -> None:
        """The area overrides the bucket and the backend is built."""
        settings = S3StorageSettings(bucket_name="configured", cluster_name="prefix")

        with patch("git.provider.config.add_builtin_storage") as mock_builtin:
            settings.build_storage("bundles")

        mock_builtin.assert_called_once_with(
            "s3", bucket_name="bundles", cluster_name="prefix"
        )

    def test_empty_cluster_name_becomes_none(self) -> None:
        """An empty cluster_name is normalized to None."""
        settings = S3StorageSettings(bucket_name="b", cluster_name="")

        with patch("git.provider.config.add_builtin_storage") as mock_builtin:
            settings.build_storage()

        mock_builtin.assert_called_once_with(
            "s3", bucket_name="b", cluster_name=None
        )


class TestAzureStorageSettingsBuildStorage:
    """Test cases for AzureStorageSettings.build_storage."""

    def test_uses_area_as_container_and_builds_backend(self) -> None:
        """The area overrides the container and the backend is built from account_url."""
        settings = AzureStorageSettings(
            account_url="https://acct.blob.core.windows.net",
            container_name="configured",
        )

        with patch("git.provider.config.add_builtin_storage") as mock_builtin:
            settings.build_storage("artifacts")

        mock_builtin.assert_called_once_with(
            "azure",
            account_url="https://acct.blob.core.windows.net",
            container_name="artifacts",
        )


class TestOciStorageSettingsBuildStorage:
    """Test cases for OciStorageSettings.build_storage."""

    def test_uses_area_as_bucket_and_builds_backend(self) -> None:
        """The area overrides the bucket and the namespace is preserved."""
        settings = OciStorageSettings(bucket_name="configured", namespace_name="ns")

        with patch("git.provider.config.add_builtin_storage") as mock_builtin:
            settings.build_storage("bundles")

        mock_builtin.assert_called_once_with(
            "oci", bucket_name="bundles", namespace_name="ns"
        )


class TestStorageSectionConfigBuildStorage:
    """Test cases for StorageSectionConfig.build_storage dispatch."""

    @staticmethod
    def _section(backend: str) -> StorageSectionConfig:
        return StorageSectionConfig(
            backend=backend,
            nexus=NexusStorageSettings(domain="d", repository="r"),
            s3=S3StorageSettings(bucket_name="b"),
            azure=AzureStorageSettings(account_url="u", container_name="c"),
            oci=OciStorageSettings(bucket_name="b", namespace_name="n"),
        )

    def test_dispatches_to_active_backend(self) -> None:
        """The active backend's settings build the storage."""
        section = self._section("azure")

        with patch("git.provider.config.add_builtin_storage") as mock_builtin:
            section.build_storage("bundles")

        mock_builtin.assert_called_once_with(
            "azure", account_url="u", container_name="bundles"
        )
