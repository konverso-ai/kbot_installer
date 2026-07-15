"""Tests for oci_storage module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from oci.exceptions import ServiceError

from storage.oci_storage import OciStorage
from utils.utils_for_unit_tests import compare


def _service_error(status: int) -> ServiceError:
    """Build an OCI ServiceError with the given HTTP status for testing."""
    return ServiceError(status, "code", {}, "message")


@pytest.fixture
def oci_client() -> MagicMock:
    """Create a mock OCI Object Storage client."""
    return MagicMock()


@pytest.fixture
def backend(oci_client: MagicMock) -> MagicMock:
    """Create a mock OCI backend."""
    mock_backend = MagicMock()
    mock_backend.get_client.return_value = oci_client
    return mock_backend


@pytest.fixture
def storage(backend: MagicMock) -> OciStorage:
    """Create an OciStorage instance for testing."""
    return OciStorage(backend=backend, bucket_name="test-bucket", namespace_name="ns")


class TestOciStorage:
    """Test cases for OciStorage class."""

    def test_ocistorage_valid_sets_attributes(self, backend: MagicMock) -> None:
        """Test OciStorage initialization."""
        instance = OciStorage(
            backend=backend, bucket_name="my-bucket", namespace_name="ns"
        )

        assert compare("eq", instance.bucket_name, "my-bucket")
        assert compare("eq", instance.namespace_name, "ns")
        assert compare("eq", instance._backend, backend)

    def test_get_name_valid_returns_name(self, storage: OciStorage) -> None:
        """Test get_name returns the storage identifier."""
        assert compare("eq", storage.get_name(), "oci")

    def test_get_bucket_name_valid_returns_bucket(self, storage: OciStorage) -> None:
        """Test get_bucket_name returns the configured bucket."""
        assert compare("eq", storage.get_bucket_name(), "test-bucket")

    def test_set_bucket_name_valid_updates_bucket(self, storage: OciStorage) -> None:
        """Test set_bucket_name updates the active bucket."""
        storage.set_bucket_name("  new-bucket  ")
        assert compare("eq", storage.bucket_name, "new-bucket")

    def test_set_bucket_name_valid_ignores_blank(self, storage: OciStorage) -> None:
        """Test set_bucket_name ignores blank values."""
        storage.set_bucket_name("   ")
        assert compare("eq", storage.bucket_name, "test-bucket")

    def test_set_valid_uploads_string(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test set uploads encoded string content."""
        storage.set("file.txt", "hello")

        oci_client.put_object.assert_called_once_with(
            "ns", "test-bucket", "file.txt", b"hello"
        )

    def test_set_valid_uploads_bytes(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test set uploads raw bytes without encoding."""
        storage.set("file.bin", b"\x00\x01")

        oci_client.put_object.assert_called_once_with(
            "ns", "test-bucket", "file.bin", b"\x00\x01"
        )

    def test_set_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test set returns early when the OCI client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )
        instance.set("file.txt", "hello")

    def test_set_valid_swallows_upload_errors(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test set logs and swallows upload failures."""
        oci_client.put_object.side_effect = RuntimeError("boom")
        storage.set("file.txt", "hello")

    def test_get_valid_returns_decoded_content(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test get returns decoded object content."""
        response = MagicMock()
        response.data.content = b"hello"
        oci_client.get_object.return_value = response

        assert compare("eq", storage.get("file.txt"), "hello")

    def test_get_valid_returns_none_without_client(self, backend: MagicMock) -> None:
        """Test get returns None when the OCI client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )

        assert compare("eq", instance.get("file.txt"), None)

    def test_get_valid_returns_none_on_not_found(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test get returns None when the object does not exist."""
        oci_client.get_object.side_effect = _service_error(404)

        assert compare("eq", storage.get("missing.txt"), None)

    def test_get_valid_returns_none_on_other_service_error(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test get returns None on non-404 service errors."""
        oci_client.get_object.side_effect = _service_error(500)

        assert compare("eq", storage.get("file.txt"), None)

    def test_get_valid_returns_none_on_generic_error(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test get returns None on unexpected retrieval errors."""
        oci_client.get_object.side_effect = RuntimeError("boom")

        assert compare("eq", storage.get("file.txt"), None)

    def test_download_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test download returns early when the OCI client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = str(Path(temp_dir) / "file.bin")
            instance.download("file.bin", local_path)

    def test_download_valid_writes_file(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test download writes object content to a local file."""
        response = MagicMock()
        response.data.raw.stream.return_value = [b"pay", b"load"]
        oci_client.get_object.return_value = response

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = str(Path(temp_dir) / "file.bin")
            storage.download("file.bin", local_path)
            assert compare("eq", Path(local_path).read_bytes(), b"payload")

    def test_delete_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test delete returns early when the OCI client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )
        instance.delete("file.txt")

    def test_delete_valid_calls_delete_object(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test delete removes a single object."""
        storage.delete("file.txt")

        oci_client.delete_object.assert_called_once_with(
            "ns", "test-bucket", "file.txt"
        )

    def test_delete_valid_swallows_delete_errors(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test delete logs and swallows deletion failures."""
        oci_client.delete_object.side_effect = RuntimeError("boom")
        storage.delete("file.txt")

    def test_delete_folder_valid_aborts_without_client(
        self, backend: MagicMock
    ) -> None:
        """Test delete_folder returns early when the OCI client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )
        instance.delete_folder("folder")

    def test_delete_folder_valid_deletes_objects(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test delete_folder deletes all objects under a prefix."""
        object_a = MagicMock()
        object_a.name = "folder/a.txt"
        object_b = MagicMock()
        object_b.name = "folder/b.txt"
        response = MagicMock()
        response.data.objects = [object_a, object_b]
        response.data.next_start_with = None
        oci_client.list_objects.return_value = response

        storage.delete_folder("folder")

        assert oci_client.delete_object.call_count == 2
        oci_client.delete_object.assert_any_call("ns", "test-bucket", "folder/a.txt")
        oci_client.delete_object.assert_any_call("ns", "test-bucket", "folder/b.txt")

    def test_delete_folder_valid_logs_when_prefix_is_empty(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test delete_folder logs when no objects match the prefix."""
        response = MagicMock()
        response.data.objects = []
        response.data.next_start_with = None
        oci_client.list_objects.return_value = response

        storage.delete_folder("missing")

        oci_client.delete_object.assert_not_called()

    def test_delete_folder_valid_swallows_errors(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test delete_folder logs and swallows deletion failures."""
        oci_client.list_objects.side_effect = RuntimeError("boom")
        storage.delete_folder("folder")

    def test_list_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test list returns early when the OCI client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )

        assert compare("eq", list(instance.list("folder/")), [])

    def test_list_valid_paginates_results(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test list follows pagination via next_start_with."""
        object_a = MagicMock()
        object_a.name = "folder/a.txt"
        object_b = MagicMock()
        object_b.name = "folder/b.txt"

        first_response = MagicMock()
        first_response.data.objects = [object_a]
        first_response.data.next_start_with = "folder/b.txt"

        second_response = MagicMock()
        second_response.data.objects = [object_b]
        second_response.data.next_start_with = None

        oci_client.list_objects.side_effect = [first_response, second_response]

        assert compare(
            "eq", list(storage.list("folder/")), ["folder/a.txt", "folder/b.txt"]
        )

    def test_list_valid_swallows_errors(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test list logs and swallows listing failures."""
        oci_client.list_objects.side_effect = RuntimeError("boom")

        assert compare("eq", list(storage.list("folder/")), [])

    def test_list_files_in_folder_valid_delegates_to_list(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test list_files_in_folder reuses list."""
        object_a = MagicMock()
        object_a.name = "folder/file.txt"
        response = MagicMock()
        response.data.objects = [object_a]
        response.data.next_start_with = None
        oci_client.list_objects.return_value = response

        assert compare(
            "eq", list(storage.list_files_in_folder("folder/")), ["folder/file.txt"]
        )

    def test_list_folders_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test list_folders returns early when the OCI client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )

        assert compare("eq", list(instance.list_folders("releases/")), [])

    def test_list_folders_valid_yields_direct_children(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test list_folders yields folders directly inside the path."""
        response = MagicMock()
        response.data.prefixes = ["releases/app/"]
        oci_client.list_objects.return_value = response

        assert compare("eq", list(storage.list_folders("releases/")), ["app"])

    def test_list_folders_valid_swallows_errors(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test list_folders logs and swallows listing failures."""
        oci_client.list_objects.side_effect = RuntimeError("boom")

        assert compare("eq", list(storage.list_folders("releases/")), [])

    def test_restore_soft_deleted_blob_invalid_raises_not_implemented(
        self, storage: OciStorage
    ) -> None:
        """Test restore_soft_deleted_blob raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            storage.restore_soft_deleted_blob("key")

    def test_check_authorization_valid_succeeds(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test check_authorization validates bucket access."""
        storage.check_authorization()

        oci_client.put_object.assert_called_once()
        oci_client.delete_object.assert_called_once()

    def test_check_authorization_invalid_raises_when_no_client(
        self, backend: MagicMock
    ) -> None:
        """Test check_authorization fails when the client is unavailable."""
        backend.get_client.return_value = None
        instance = OciStorage(
            backend=backend, bucket_name="test-bucket", namespace_name="ns"
        )

        with pytest.raises(RuntimeError, match="Authentication failed"):
            instance.check_authorization()

    @pytest.mark.parametrize("status_code", [401, 403])
    def test_check_authorization_invalid_raises_on_access_denied(
        self,
        storage: OciStorage,
        oci_client: MagicMock,
        status_code: int,
    ) -> None:
        """Test check_authorization maps auth/permission errors to RuntimeError."""
        oci_client.put_object.side_effect = _service_error(status_code)

        with pytest.raises(RuntimeError, match="permissions"):
            storage.check_authorization()

    def test_check_authorization_invalid_raises_on_unexpected_service_error(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test check_authorization wraps unexpected service errors."""
        oci_client.put_object.side_effect = _service_error(500)

        with pytest.raises(RuntimeError, match="Unexpected error"):
            storage.check_authorization()

    def test_check_authorization_invalid_raises_on_unexpected_error(
        self, storage: OciStorage, oci_client: MagicMock
    ) -> None:
        """Test check_authorization wraps unexpected errors."""
        oci_client.put_object.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            storage.check_authorization()
