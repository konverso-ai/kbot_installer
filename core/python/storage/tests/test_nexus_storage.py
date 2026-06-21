"""Tests for nexus_storage module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth.base import HttpAuthBase
from service.errors import NexusHttpError
from storage.nexus_storage import NexusStorage
from utils.utils_for_unit_tests import compare


class TestNexusStorage:
    """Test cases for NexusStorage class."""

    @pytest.fixture
    def storage(self) -> NexusStorage:
        """Create a NexusStorage instance for testing."""
        return NexusStorage(domain="konverso.ai", repository="kbot_raw", auth=None)

    @pytest.fixture
    def storage_with_auth(self) -> NexusStorage:
        """Create a NexusStorage instance with authentication."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        return NexusStorage(
            domain="konverso.ai",
            repository="kbot_raw",
            auth=mock_auth,
        )

    def test_initialization_valid_sets_attributes(self) -> None:
        """Test NexusStorage initialization."""
        storage = NexusStorage("konverso.ai", "kbot_raw")

        assert compare("eq", storage.domain, "konverso.ai")
        assert compare("eq", storage.repository, "kbot_raw")
        assert compare("eq", storage._auth, None)

    def test_get_name_valid_returns_name(self) -> None:
        """Test get_name returns the storage identifier."""
        storage = NexusStorage("konverso.ai", "kbot_raw")

        assert compare("eq", storage.get_name(), "nexus")

    def test_initialization_valid_with_auth(self) -> None:
        """Test NexusStorage initialization with authentication."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        storage = NexusStorage("konverso.ai", "kbot_raw", mock_auth)

        assert compare("eq", storage.domain, "konverso.ai")
        assert compare("eq", storage.repository, "kbot_raw")
        assert compare("eq", storage._auth, mock_auth)

    def test_normalize_key_valid_returns_empty_for_missing_path(
        self, storage: NexusStorage
    ) -> None:
        """Test _normalize_key returns an empty string for missing paths."""
        assert compare("eq", storage._normalize_key(None), "")

    def test_list_folders_valid_skips_files_without_subfolders(
        self, storage: NexusStorage
    ) -> None:
        """Test list_folders ignores files directly inside the path."""
        mock_files = [
            MagicMock(path="/kbot_raw/releases/readme.txt"),
            MagicMock(path="/kbot_raw/releases/app/file.tar.gz"),
        ]
        mock_service = MagicMock()
        mock_service.list_repository = AsyncMock(
            return_value=MagicMock(__iter__=MagicMock(return_value=iter(mock_files)))
        )
        storage._service = mock_service

        assert compare("eq", list(storage.list_folders("releases/")), ["app"])

    def test_normalize_key_valid_strips_repository_prefix(
        self, storage: NexusStorage
    ) -> None:
        """Test _normalize_key removes the repository prefix from paths."""
        assert compare(
            "eq",
            storage._normalize_key("/kbot_raw/folder/file.tar.gz"),
            "folder/file.tar.gz",
        )

    def test_normalize_prefix_valid_appends_trailing_slash(
        self, storage: NexusStorage
    ) -> None:
        """Test _normalize_prefix appends a trailing slash."""
        assert compare("eq", storage._normalize_prefix("folder"), "folder/")

    def test_get_valid_returns_none_on_download_error(
        self, storage: NexusStorage
    ) -> None:
        """Test get returns None when download fails."""
        mock_service = MagicMock()
        mock_service.file_exists = AsyncMock(return_value=True)
        mock_service.get_file = AsyncMock(side_effect=RuntimeError("boom"))
        storage._service = mock_service

        assert compare("eq", storage.get("file.txt"), None)

    def test_list_files_in_folder_valid_yields_direct_children(
        self, storage: NexusStorage
    ) -> None:
        """Test list_files_in_folder yields files directly inside a folder."""
        mock_files = [
            MagicMock(path="/kbot_raw/folder/file.tar.gz"),
            MagicMock(path="/kbot_raw/folder/sub/file.tar.gz"),
        ]
        mock_service = MagicMock()
        mock_service.list_repository = AsyncMock(
            return_value=MagicMock(__iter__=MagicMock(return_value=iter(mock_files)))
        )
        storage._service = mock_service

        assert compare(
            "eq",
            list(storage.list_files_in_folder("folder/")),
            ["folder/file.tar.gz"],
        )

    def test_list_folders_valid_deduplicates_folder_names(
        self, storage: NexusStorage
    ) -> None:
        """Test list_folders yields each folder name only once."""
        mock_files = [
            MagicMock(path="/kbot_raw/releases/app/a.tar.gz"),
            MagicMock(path="/kbot_raw/releases/app/b.tar.gz"),
        ]
        mock_service = MagicMock()
        mock_service.list_repository = AsyncMock(
            return_value=MagicMock(__iter__=MagicMock(return_value=iter(mock_files)))
        )
        storage._service = mock_service

        assert compare("eq", list(storage.list_folders("releases/")), ["app"])

    def test_repository_path_valid_builds_path(self, storage: NexusStorage) -> None:
        """Test _repository_path builds the repository path."""
        assert compare(
            "eq",
            storage._repository_path("test_repo.tar.gz"),
            "/kbot_raw/test_repo.tar.gz",
        )

    def test_exists_valid_returns_true(self, storage: NexusStorage) -> None:
        """Test exists returns True when the object is reachable."""
        mock_service = MagicMock()
        mock_service.file_exists = AsyncMock(return_value=True)
        storage._service = mock_service

        assert compare("eq", storage.exists("test_repo.tar.gz"), True)
        mock_service.file_exists.assert_awaited_once_with(
            "/kbot_raw/test_repo.tar.gz"
        )

    def test_exists_valid_returns_false(self, storage: NexusStorage) -> None:
        """Test exists returns False when the object is missing."""
        mock_service = MagicMock()
        mock_service.file_exists = AsyncMock(return_value=False)
        storage._service = mock_service

        assert compare("eq", storage.exists("missing.tar.gz"), False)

    def test_download_valid_calls_service(self, storage: NexusStorage) -> None:
        """Test download delegates to NexusService.download_and_extract."""
        mock_service = MagicMock()
        mock_service.download_and_extract = AsyncMock(return_value=None)
        storage._service = mock_service

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "extracted"
            target_dir.mkdir()
            storage.download("test_repo.tar.gz", str(target_dir))

        mock_service.download_and_extract.assert_awaited_once_with(
            "/kbot_raw/test_repo.tar.gz",
            str(target_dir),
        )

    def test_get_valid_returns_content(self, storage: NexusStorage) -> None:
        """Test get returns decoded object content."""
        mock_service = MagicMock()
        mock_service.file_exists = AsyncMock(return_value=True)

        def write_file(_path: str, local_path: str) -> None:
            Path(local_path).write_text("hello", encoding="utf-8")

        mock_service.get_file = AsyncMock(side_effect=write_file)
        storage._service = mock_service

        assert compare("eq", storage.get("file.txt"), "hello")

    def test_get_valid_returns_none_when_missing(
        self, storage: NexusStorage
    ) -> None:
        """Test get returns None when the object does not exist."""
        with patch.object(storage, "exists", return_value=False):
            assert compare("eq", storage.get("missing.txt"), None)

    def test_list_valid_yields_matching_keys(self, storage: NexusStorage) -> None:
        """Test list yields keys under the requested prefix."""
        mock_file = MagicMock()
        mock_file.path = "/kbot_raw/folder/file.tar.gz"
        mock_files = MagicMock()
        mock_files.__iter__ = MagicMock(return_value=iter([mock_file]))
        mock_service = MagicMock()
        mock_service.list_repository = AsyncMock(return_value=mock_files)
        storage._service = mock_service

        assert compare(
            "eq",
            list(storage.list("folder/")),
            ["folder/file.tar.gz"],
        )

    def test_list_folders_valid_yields_direct_children(
        self, storage: NexusStorage
    ) -> None:
        """Test list_folders yields folders directly inside the path."""
        mock_files = [
            MagicMock(path="/kbot_raw/releases/app/file.tar.gz"),
            MagicMock(path="/kbot_raw/releases/lib/file.tar.gz"),
        ]
        mock_service = MagicMock()
        mock_service.list_repository = AsyncMock(
            return_value=MagicMock(__iter__=MagicMock(return_value=iter(mock_files)))
        )
        storage._service = mock_service

        assert compare("eq", list(storage.list_folders("releases/")), ["app", "lib"])

    @pytest.mark.parametrize(
        "method_name",
        ["set", "delete", "delete_folder", "restore_soft_deleted_blob"],
    )
    def test_unsupported_methods_invalid_raise_not_implemented(
        self, storage: NexusStorage, method_name: str
    ) -> None:
        """Test unsupported storage operations raise NotImplementedError."""
        method = getattr(storage, method_name)
        with pytest.raises(NotImplementedError):
            if method_name == "set":
                method("key", "value")
            elif method_name == "restore_soft_deleted_blob":
                method("key")
            else:
                method("key")

    def test_download_invalid_propagates_http_error(
        self, storage: NexusStorage
    ) -> None:
        """Test download propagates Nexus HTTP errors."""
        mock_service = MagicMock()
        mock_service.download_and_extract = AsyncMock(
            side_effect=NexusHttpError(404, "Not found")
        )
        storage._service = mock_service

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(NexusHttpError):
                storage.download("missing.tar.gz", temp_dir)
