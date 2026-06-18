"""Tests for azure_storage module."""

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError
from azure.storage.blob import BlobPrefix

from storage.azure_storage import AzureStorage
from utils.utils_for_unit_tests import compare


@pytest.fixture
def container_client() -> MagicMock:
    """Create a mock Azure container client."""
    return MagicMock()


@pytest.fixture
def blob_service_client(container_client: MagicMock) -> MagicMock:
    """Create a mock Azure blob service client."""
    client = MagicMock()
    client.get_container_client.return_value = container_client
    return client


@pytest.fixture
def backend(blob_service_client: MagicMock) -> MagicMock:
    """Create a mock Azure backend."""
    mock_backend = MagicMock()
    mock_backend.account_url = "https://account.blob.core.windows.net"
    mock_backend.get_client.return_value = blob_service_client
    return mock_backend


@pytest.fixture
def storage(backend: MagicMock) -> AzureStorage:
    """Create an AzureStorage instance for testing."""
    return AzureStorage(backend=backend, container_name="test-container")


class TestAzureStorage:
    """Test cases for AzureStorage class."""

    def test_azurestorage_valid_sets_attributes(self, backend: MagicMock) -> None:
        """Test AzureStorage initialization."""
        instance = AzureStorage(backend=backend, container_name="my-container")

        assert compare("eq", instance.container_name, "my-container")
        assert compare("eq", instance._backend, backend)

    def test_get_name_valid_returns_name(self, storage: AzureStorage) -> None:
        """Test get_name returns the storage identifier."""
        assert compare("eq", storage.get_name(), "azure")

    def test_get_container_name_valid_returns_container(self, storage: AzureStorage) -> None:
        """Test get_container_name returns the configured container."""
        assert compare("eq", storage.get_container_name(), "test-container")

    def test_set_container_name_valid_updates_container(self, storage: AzureStorage) -> None:
        """Test set_container_name updates the active container."""
        storage.set_container_name("  new-container  ")
        assert compare("eq", storage.container_name, "new-container")

    def test_set_container_name_valid_ignores_blank(self, storage: AzureStorage) -> None:
        """Test set_container_name ignores blank values."""
        storage.set_container_name("   ")
        assert compare("eq", storage.container_name, "test-container")

    def test_set_valid_uploads_string(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test set uploads encoded string content."""
        storage.set("file.txt", "hello")

        container_client.upload_blob.assert_called_once_with(
            name="file.txt",
            data=b"hello",
            overwrite=True,
        )

    def test_set_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test set returns early when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")
        instance.set("file.txt", "hello")

    def test_get_valid_returns_decoded_content(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test get returns decoded blob content."""
        blob_client = MagicMock()
        blob_client.download_blob.return_value.readall.return_value = b"hello"
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.get("file.txt"), "hello")

    def test_get_valid_returns_none_on_missing_blob(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test get returns None when the blob does not exist."""
        blob_client = MagicMock()
        blob_client.download_blob.side_effect = ResourceNotFoundError("missing")
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.get("missing.txt"), None)

    def test_get_valid_returns_none_without_client(self, backend: MagicMock) -> None:
        """Test get returns None when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")

        assert compare("eq", instance.get("file.txt"), None)

    def test_get_valid_returns_none_on_generic_error(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test get returns None on unexpected retrieval errors."""
        blob_client = MagicMock()
        blob_client.download_blob.side_effect = RuntimeError("boom")
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.get("file.txt"), None)

    def test_set_valid_swallows_upload_errors(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test set logs and swallows upload failures."""
        container_client.upload_blob.side_effect = RuntimeError("boom")
        storage.set("file.txt", "hello")

    def test_download_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test download returns early when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = str(Path(temp_dir) / "file.bin")
            instance.download("file.bin", local_path)

    def test_list_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test list returns early when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")

        assert compare("eq", list(instance.list("folder")), [])

    def test_list_valid_swallows_errors(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test list logs and swallows listing failures."""
        container_client.list_blobs.side_effect = RuntimeError("boom")

        assert compare("eq", list(storage.list("folder")), [])

    def test_list_folders_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test list_folders returns early when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")

        assert compare("eq", list(instance.list_folders("releases")), [])

    def test_list_folders_valid_swallows_errors(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test list_folders logs and swallows listing failures."""
        container_client.walk_blobs.side_effect = RuntimeError("boom")

        assert compare("eq", list(storage.list_folders("releases")), [])

    def test_delete_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test delete returns early when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")
        instance.delete("file.txt")

    def test_delete_folder_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test delete_folder returns early when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")
        instance.delete_folder("folder")

    def test_restore_soft_deleted_blob_valid_returns_false_on_undelete_error(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test restore_soft_deleted_blob returns False on undelete failures."""
        blob_client = MagicMock()
        deleted_properties = MagicMock()
        deleted_properties.deleted = True
        blob_client.get_blob_properties.return_value = deleted_properties
        blob_client.undelete_blob.side_effect = RuntimeError("boom")
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.restore_soft_deleted_blob("file.txt"), False)

    def test_download_valid_writes_file(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test download writes blob content to a local file."""
        blob_client = MagicMock()
        blob_data = MagicMock()

        def write_into(file_obj) -> None:
            file_obj.write(b"payload")

        blob_data.readinto.side_effect = write_into
        blob_client.download_blob.return_value = blob_data
        container_client.get_blob_client.return_value = blob_client

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = str(Path(temp_dir) / "file.bin")
            storage.download("file.bin", local_path)
            assert compare("eq", Path(local_path).read_bytes(), b"payload")

    def test_list_valid_yields_blob_names(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test list yields blob names under a prefix."""
        blob_a = MagicMock()
        blob_a.name = "folder/file.txt"
        container_client.list_blobs.return_value = [blob_a]

        assert compare("eq", list(storage.list("folder")), ["folder/file.txt"])
        container_client.list_blobs.assert_called_once_with(name_starts_with="folder/")

    def test_list_files_in_folder_valid_delegates_to_list(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test list_files_in_folder reuses list."""
        blob_a = MagicMock()
        blob_a.name = "folder/file.txt"
        container_client.list_blobs.return_value = [blob_a]

        assert compare("eq", list(storage.list_files_in_folder("folder")), ["folder/file.txt"])

    def test_list_folders_valid_yields_direct_children(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test list_folders yields folders directly inside the path."""
        folder_prefix = MagicMock(spec=BlobPrefix)
        folder_prefix.prefix = "releases/app/"
        container_client.walk_blobs.return_value = [folder_prefix]

        with patch(
            "storage.azure_storage.isinstance",
            side_effect=lambda obj, cls: obj is folder_prefix and cls is BlobPrefix,
        ):
            assert compare("eq", list(storage.list_folders("releases")), ["app"])

    def test_delete_valid_swallows_delete_errors(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test delete logs and swallows deletion failures."""
        container_client.delete_blob.side_effect = RuntimeError("boom")
        storage.delete("file.txt")

    def test_delete_valid_calls_delete_blob(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test delete removes a single blob."""
        storage.delete("file.txt")

        container_client.delete_blob.assert_called_once_with("file.txt")

    def test_delete_folder_valid_deletes_blobs_in_chunks(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test delete_folder deletes all blobs under a prefix."""
        blob_a = MagicMock()
        blob_a.name = "folder/a.txt"
        blob_b = MagicMock()
        blob_b.name = "folder/b.txt"
        container_client.list_blobs.return_value = [blob_a, blob_b]

        storage.delete_folder("folder")

        container_client.delete_blobs.assert_called_once_with(
            "folder/a.txt",
            "folder/b.txt",
        )

    def test_delete_folder_valid_returns_when_empty(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test delete_folder returns when no blobs match the prefix."""
        container_client.list_blobs.return_value = []

        storage.delete_folder("missing")

        container_client.delete_blobs.assert_not_called()

    def test_restore_soft_deleted_blob_valid_returns_true_when_not_deleted(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test restore_soft_deleted_blob returns True for active blobs."""
        blob_client = MagicMock()
        blob_client.get_blob_properties.return_value.deleted = False
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.restore_soft_deleted_blob("file.txt"), True)

    def test_restore_soft_deleted_blob_valid_restores_deleted_blob(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test restore_soft_deleted_blob undeletes soft-deleted blobs."""
        blob_client = MagicMock()
        deleted_properties = MagicMock()
        deleted_properties.deleted = True
        restored_properties = MagicMock()
        restored_properties.deleted = False
        blob_client.get_blob_properties.side_effect = [
            deleted_properties,
            restored_properties,
        ]
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.restore_soft_deleted_blob("file.txt"), True)
        blob_client.undelete_blob.assert_called_once()

    def test_restore_soft_deleted_blob_valid_returns_false_without_client(
        self, backend: MagicMock
    ) -> None:
        """Test restore_soft_deleted_blob returns False without a container client."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")

        assert compare("eq", instance.restore_soft_deleted_blob("file.txt"), False)

    def test_restore_soft_deleted_blob_valid_returns_false_on_blob_client_error(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test restore_soft_deleted_blob returns False when blob client creation fails."""
        container_client.get_blob_client.side_effect = RuntimeError("client error")

        assert compare("eq", storage.restore_soft_deleted_blob("file.txt"), False)

    def test_restore_soft_deleted_blob_valid_returns_false_on_properties_error(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test restore_soft_deleted_blob returns False when properties cannot be read."""
        blob_client = MagicMock()
        blob_client.get_blob_properties.side_effect = RuntimeError("properties error")
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.restore_soft_deleted_blob("file.txt"), False)

    def test_restore_soft_deleted_blob_valid_returns_false_on_not_found(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test restore_soft_deleted_blob returns False when undelete fails."""
        blob_client = MagicMock()
        deleted_properties = MagicMock()
        deleted_properties.deleted = True
        blob_client.get_blob_properties.return_value = deleted_properties
        blob_client.undelete_blob.side_effect = ResourceNotFoundError("missing")
        container_client.get_blob_client.return_value = blob_client

        assert compare("eq", storage.restore_soft_deleted_blob("file.txt"), False)

    def test_check_authorization_valid_succeeds(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test check_authorization validates container access."""
        storage.check_authorization()

        container_client.upload_blob.assert_called_once()
        container_client.delete_blob.assert_called_once_with("temp_blob_for_checking")

    def test_check_authorization_invalid_raises_when_no_client(
        self, backend: MagicMock
    ) -> None:
        """Test check_authorization fails when the container client is unavailable."""
        backend.get_client.return_value = None
        instance = AzureStorage(backend=backend, container_name="test-container")

        with pytest.raises(RuntimeError, match="Authentication failed"):
            instance.check_authorization()

    def test_check_authorization_invalid_raises_on_client_authentication_error(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test check_authorization maps authentication errors to RuntimeError."""
        container_client.upload_blob.side_effect = ClientAuthenticationError(
            message="invalid credentials"
        )

        with pytest.raises(RuntimeError, match="SAS token"):
            storage.check_authorization()

    def test_check_authorization_invalid_raises_on_unexpected_error(
        self, storage: AzureStorage, container_client: MagicMock
    ) -> None:
        """Test check_authorization wraps unexpected errors."""
        container_client.upload_blob.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            storage.check_authorization()
