"""Tests for service.nexus_file module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from service.checksum import Checksum
from service.errors import NexusHttpError
from service.nexus_file import NexusFile
from utils.utils_for_unit_tests import compare


class TestFromJson:
    """Test cases for NexusFile.from_json."""

    def test_from_json_valid_builds_instance_bound_to_service(self) -> None:
        """Test that from_json builds a NexusFile bound to the given service."""
        service = MagicMock()
        data = {"path": "/repo/file.txt", "repository": "repo"}

        file = NexusFile.from_json(data, service=service)

        assert compare("eq", file.path, "/repo/file.txt")
        assert compare("eq", file.repository, "repo")
        assert compare("eq", file._service, service)  # noqa: SLF001

    def test_from_json_valid_maps_aliased_fields(self) -> None:
        """Test that camelCase Nexus API keys are mapped to snake_case fields."""
        data = {
            "downloadUrl": "https://nexus/example",
            "contentType": "application/zip",
            "lastModified": "2024-01-01T00:00:00Z",
            "lastDownloaded": "2024-01-02T00:00:00Z",
            "uploaderIp": "10.0.0.1",
            "fileSize": 42,
            "blobCreated": "2024-01-01T00:00:00Z",
            "blobStoreName": "default",
            "blobUpdated": "2024-01-01T00:00:00Z",
            "blobRef": "ref-1",
            "lastVerified": "2024-01-03T00:00:00Z",
        }

        file = NexusFile.from_json(data, service=MagicMock())

        assert compare("eq", file.download_url, "https://nexus/example")
        assert compare("eq", file.content_type, "application/zip")
        assert compare("eq", file.last_modified, "2024-01-01T00:00:00Z")
        assert compare("eq", file.last_downloaded, "2024-01-02T00:00:00Z")
        assert compare("eq", file.uploader_ip, "10.0.0.1")
        assert compare("eq", file.file_size, 42)
        assert compare("eq", file.blob_created, "2024-01-01T00:00:00Z")
        assert compare("eq", file.blob_store_name, "default")
        assert compare("eq", file.blob_updated, "2024-01-01T00:00:00Z")
        assert compare("eq", file.blob_ref, "ref-1")
        assert compare("eq", file.last_verified, "2024-01-03T00:00:00Z")

    def test_from_json_valid_builds_checksum_from_payload(self) -> None:
        """Test that a checksum mapping in the payload is parsed into a Checksum."""
        data = {"checksum": {"md5": "abc", "sha1": "def"}}

        file = NexusFile.from_json(data, service=MagicMock())

        assert compare("eq", file.checksum, Checksum(md5="abc", sha1="def"))

    def test_from_json_valid_defaults_checksum_when_missing(self) -> None:
        """Test that a missing checksum key defaults to an empty Checksum."""
        file = NexusFile.from_json({}, service=MagicMock())

        assert compare("eq", file.checksum, Checksum())

    def test_from_json_valid_preserves_raw_payload_field(self) -> None:
        """Test that an explicit raw field is preserved as-is."""
        file = NexusFile.from_json({"raw": {"extra": "value"}}, service=MagicMock())

        assert compare("eq", file.raw, {"extra": "value"})

    def test_from_json_valid_defaults_raw_when_missing(self) -> None:
        """Test that raw defaults to an empty dict when not provided."""
        file = NexusFile.from_json({}, service=MagicMock())

        assert compare("eq", file.raw, {})


class TestStrAndRepr:
    """Test cases for __str__ and __repr__."""

    def test_str_valid_includes_path(self) -> None:
        """Test that str() includes the file's path."""
        file = NexusFile.from_json({"path": "/repo/file.txt"}, service=MagicMock())

        assert compare("eq", str(file), "NexusFile(/repo/file.txt)")

    def test_str_valid_with_no_path(self) -> None:
        """Test that str() handles a missing path gracefully."""
        file = NexusFile.from_json({}, service=MagicMock())

        assert compare("eq", str(file), "NexusFile(None)")

    def test_repr_valid_matches_str(self) -> None:
        """Test that repr() returns the same value as str()."""
        file = NexusFile.from_json({"path": "/repo/file.txt"}, service=MagicMock())

        assert compare("eq", repr(file), str(file))


class TestFolderAndFileName:
    """Test cases for the folder_name and file_name computed fields."""

    def test_folder_name_valid_returns_folder_portion(self) -> None:
        """Test that folder_name returns everything before the last '/'."""
        file = NexusFile.from_json(
            {"path": "/releases/app/file.txt"}, service=MagicMock()
        )

        assert compare("eq", file.folder_name, "releases/app")

    def test_folder_name_valid_strips_leading_slash(self) -> None:
        """Test that folder_name normalizes a leading slash before splitting."""
        file = NexusFile.from_json({"path": "/folder/file.txt"}, service=MagicMock())

        assert compare("eq", file.folder_name, "folder")

    def test_folder_name_none_when_no_path(self) -> None:
        """Test that folder_name is None when path is not set."""
        file = NexusFile.from_json({}, service=MagicMock())

        assert compare("eq", file.folder_name, None)

    def test_file_name_valid_returns_last_segment(self) -> None:
        """Test that file_name returns the segment after the last '/'."""
        file = NexusFile.from_json(
            {"path": "/releases/app/file.txt"}, service=MagicMock()
        )

        assert compare("eq", file.file_name, "file.txt")

    def test_file_name_none_when_no_path(self) -> None:
        """Test that file_name is None when path is not set."""
        file = NexusFile.from_json({}, service=MagicMock())

        assert compare("eq", file.file_name, None)

    def test_folder_name_valid_when_path_has_no_folder(self) -> None:
        """Test that folder_name returns the whole path when there is no folder."""
        file = NexusFile.from_json({"path": "file.txt"}, service=MagicMock())

        assert compare("eq", file.folder_name, "file.txt")

    def test_file_name_valid_when_path_has_no_folder(self) -> None:
        """Test that file_name returns the whole path when there is no folder."""
        file = NexusFile.from_json({"path": "file.txt"}, service=MagicMock())

        assert compare("eq", file.file_name, "file.txt")


class TestDownload:
    """Test cases for the async download method."""

    @pytest.mark.asyncio
    async def test_download_valid_calls_service_with_repository_and_path(
        self,
    ) -> None:
        """Test that download delegates to the service with the full asset path."""
        service = MagicMock()
        service.get_file = AsyncMock()
        file = NexusFile.from_json(
            {"path": "/folder/file.txt", "repository": "my-repo"}, service=service
        )

        await file.download("/tmp/file.txt")

        service.get_file.assert_awaited_once_with(
            "/my-repo/folder/file.txt", "/tmp/file.txt"
        )

    @pytest.mark.asyncio
    async def test_download_valid_defaults_repository_to_empty_string(self) -> None:
        """Test that download uses an empty repository segment when unset."""
        service = MagicMock()
        service.get_file = AsyncMock()
        file = NexusFile.from_json({"path": "/folder/file.txt"}, service=service)

        await file.download("/tmp/file.txt")

        service.get_file.assert_awaited_once_with(
            "//folder/file.txt", "/tmp/file.txt"
        )

    @pytest.mark.asyncio
    async def test_download_raises_when_no_path(self) -> None:
        """Test that download raises NexusHttpError(400) when path is missing."""
        file = NexusFile.from_json({}, service=MagicMock())

        with pytest.raises(NexusHttpError) as exc_info:
            await file.download("/tmp/file.txt")

        assert compare("eq", exc_info.value.status_code, 400)
