"""Tests for s3_storage module."""

import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from storage.s3_storage import S3Storage
from utils.utils_for_unit_tests import compare


@pytest.fixture
def s3_client() -> MagicMock:
    """Create a mock S3 client."""
    return MagicMock()


@pytest.fixture
def backend(s3_client: MagicMock) -> MagicMock:
    """Create a mock S3 backend."""
    mock_backend = MagicMock()
    mock_backend.get_client.return_value = s3_client
    return mock_backend


@pytest.fixture
def storage(backend: MagicMock) -> S3Storage:
    """Create an S3Storage instance for testing."""
    return S3Storage(backend=backend, bucket_name="test-bucket")


class TestS3Storage:
    """Test cases for S3Storage class."""

    def test_s3storage_valid_sets_attributes(self, backend: MagicMock) -> None:
        """Test S3Storage initialization."""
        instance = S3Storage(backend=backend, bucket_name="my-bucket", cluster_name="cluster")

        assert compare("eq", instance.bucket_name, "my-bucket")
        assert compare("eq", instance.cluster_name, "cluster")
        assert compare("eq", instance._backend, backend)

    def test_get_name_valid_returns_name(self, storage: S3Storage) -> None:
        """Test get_name returns the storage identifier."""
        assert compare("eq", storage.get_name(), "s3")

    @pytest.mark.parametrize(
        "key, cluster_name, expected",
        [
            ("file.txt", None, "file.txt"),
            ("file.txt", "cluster", "cluster/file.txt"),
        ],
    )
    def test_prefixed_key_valid_builds_key(
        self,
        backend: MagicMock,
        key: str,
        cluster_name: str | None,
        expected: str,
    ) -> None:
        """Test _prefixed_key applies the cluster prefix when configured."""
        instance = S3Storage(backend=backend, bucket_name="bucket", cluster_name=cluster_name)
        assert compare("eq", instance._prefixed_key(key), expected)

    @pytest.mark.parametrize(
        "prefix, cluster_name, expected",
        [
            ("", None, ""),
            ("folder", None, "folder/"),
            ("", "cluster", "cluster/"),
            ("folder", "cluster", "cluster/folder/"),
        ],
    )
    def test_storage_prefix_valid_builds_prefix(
        self,
        backend: MagicMock,
        prefix: str,
        cluster_name: str | None,
        expected: str,
    ) -> None:
        """Test _storage_prefix normalizes list prefixes."""
        instance = S3Storage(backend=backend, bucket_name="bucket", cluster_name=cluster_name)
        assert compare("eq", instance._storage_prefix(prefix), expected)

    def test_get_bucket_name_valid_returns_bucket(self, storage: S3Storage) -> None:
        """Test get_bucket_name returns the configured bucket."""
        assert compare("eq", storage.get_bucket_name(), "test-bucket")

    def test_set_bucket_name_valid_updates_bucket(self, storage: S3Storage) -> None:
        """Test set_bucket_name updates the active bucket."""
        storage.set_bucket_name("  new-bucket  ")
        assert compare("eq", storage.bucket_name, "new-bucket")

    def test_set_bucket_name_valid_ignores_blank(self, storage: S3Storage) -> None:
        """Test set_bucket_name ignores blank values."""
        storage.set_bucket_name("   ")
        assert compare("eq", storage.bucket_name, "test-bucket")

    def test_set_valid_uploads_string(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test set uploads encoded string content."""
        storage.set("file.txt", "hello")

        s3_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="file.txt",
            Body=b"hello",
        )

    def test_set_valid_uploads_bytes(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test set uploads raw bytes without encoding."""
        storage.set("file.bin", b"\x00\x01")

        s3_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="file.bin",
            Body=b"\x00\x01",
        )

    def test_set_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test set returns early when the S3 client is unavailable."""
        backend.get_client.return_value = None
        instance = S3Storage(backend=backend, bucket_name="test-bucket")
        instance.set("file.txt", "hello")

    def test_get_valid_returns_decoded_content(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test get returns decoded object content."""
        s3_client.get_object.return_value = {"Body": BytesIO(b"hello")}

        assert compare("eq", storage.get("file.txt"), "hello")

    def test_get_valid_returns_none_without_client(self, backend: MagicMock) -> None:
        """Test get returns None when the S3 client is unavailable."""
        backend.get_client.return_value = None
        instance = S3Storage(backend=backend, bucket_name="test-bucket")

        assert compare("eq", instance.get("file.txt"), None)

    def test_get_valid_returns_none_on_nosuchkey(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test get returns None when the object does not exist."""
        s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        assert compare("eq", storage.get("missing.txt"), None)

    def test_get_valid_returns_none_on_generic_error(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test get returns None on unexpected retrieval errors."""
        s3_client.get_object.side_effect = RuntimeError("boom")

        assert compare("eq", storage.get("file.txt"), None)

    def test_get_valid_returns_none_on_other_client_error(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test get returns None on non-NoSuchKey client errors."""
        s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Server error"}},
            "GetObject",
        )

        assert compare("eq", storage.get("file.txt"), None)

    def test_set_valid_swallows_upload_errors(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test set logs and swallows upload failures."""
        s3_client.put_object.side_effect = RuntimeError("boom")
        storage.set("file.txt", "hello")

    def test_download_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test download returns early when the S3 client is unavailable."""
        backend.get_client.return_value = None
        instance = S3Storage(backend=backend, bucket_name="test-bucket")

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = str(Path(temp_dir) / "file.bin")
            instance.download("file.bin", local_path)

    def test_delete_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test delete returns early when the S3 client is unavailable."""
        backend.get_client.return_value = None
        instance = S3Storage(backend=backend, bucket_name="test-bucket")
        instance.delete("file.txt")

    def test_delete_valid_swallows_delete_errors(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test delete logs and swallows deletion failures."""
        s3_client.delete_object.side_effect = RuntimeError("boom")
        storage.delete("file.txt")

    def test_delete_folder_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test delete_folder returns early when the S3 client is unavailable."""
        backend.get_client.return_value = None
        instance = S3Storage(backend=backend, bucket_name="test-bucket")
        instance.delete_folder("folder")

    def test_delete_folder_valid_logs_when_prefix_is_empty(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test delete_folder logs when no objects match the prefix."""
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Contents": []}]
        s3_client.get_paginator.return_value = paginator

        storage.delete_folder("missing")

        s3_client.delete_objects.assert_not_called()

    def test_delete_folder_valid_swallows_errors(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test delete_folder logs and swallows deletion failures."""
        s3_client.get_paginator.side_effect = RuntimeError("boom")
        storage.delete_folder("folder")

    def test_list_valid_aborts_without_client(self, backend: MagicMock) -> None:
        """Test list returns early when the S3 client is unavailable."""
        backend.get_client.return_value = None
        instance = S3Storage(backend=backend, bucket_name="test-bucket")

        assert compare("eq", list(instance.list("folder/")), [])

    def test_list_valid_skips_pages_without_contents(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test list ignores pages without object contents."""
        paginator = MagicMock()
        paginator.paginate.return_value = [{}, {"Contents": [{"Key": "file.txt"}]}]
        s3_client.get_paginator.return_value = paginator

        assert compare("eq", list(storage.list()), ["file.txt"])

    def test_list_valid_swallows_errors(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test list logs and swallows listing failures."""
        s3_client.get_paginator.side_effect = RuntimeError("boom")

        assert compare("eq", list(storage.list("folder/")), [])

    def test_check_authorization_invalid_raises_on_unexpected_error(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test check_authorization wraps unexpected errors."""
        s3_client.put_object.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            storage.check_authorization()

    def test_download_valid_writes_file(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test download writes object content to a local file."""
        def write_file(_bucket: str, _key: str, file_obj) -> None:
            file_obj.write(b"payload")

        s3_client.download_fileobj.side_effect = write_file

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = str(Path(temp_dir) / "file.bin")
            storage.download("file.bin", local_path)
            assert compare("eq", Path(local_path).read_bytes(), b"payload")

    def test_delete_valid_calls_delete_object(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test delete removes a single object."""
        storage.delete("file.txt")

        s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="file.txt",
        )

    def test_delete_folder_valid_deletes_objects_in_chunks(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test delete_folder deletes all objects under a prefix."""
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "folder/a.txt"}, {"Key": "folder/b.txt"}]},
        ]
        s3_client.get_paginator.return_value = paginator

        storage.delete_folder("folder")

        s3_client.delete_objects.assert_called_once_with(
            Bucket="test-bucket",
            Delete={"Objects": [{"Key": "folder/a.txt"}, {"Key": "folder/b.txt"}]},
        )

    def test_delete_folder_valid_skips_empty_pages(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test delete_folder ignores pages without contents."""
        paginator = MagicMock()
        paginator.paginate.return_value = [{}, {"Contents": [{"Key": "folder/a.txt"}]}]
        s3_client.get_paginator.return_value = paginator

        storage.delete_folder("folder")

        s3_client.delete_objects.assert_called_once()

    def test_list_valid_strips_cluster_prefix(
        self, backend: MagicMock, s3_client: MagicMock
    ) -> None:
        """Test list yields keys without the cluster prefix."""
        instance = S3Storage(backend=backend, bucket_name="bucket", cluster_name="cluster")
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "cluster/folder/file.txt"}]},
        ]
        s3_client.get_paginator.return_value = paginator

        assert compare("eq", list(instance.list("folder/")), ["folder/file.txt"])

    def test_list_files_in_folder_valid_delegates_to_list(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test list_files_in_folder reuses list."""
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "folder/file.txt"}]},
        ]
        s3_client.get_paginator.return_value = paginator

        assert compare("eq", list(storage.list_files_in_folder("folder/")), ["folder/file.txt"])

    @pytest.mark.parametrize(
        "method_name",
        ["list_folders", "restore_soft_deleted_blob"],
    )
    def test_unsupported_methods_invalid_raise_not_implemented(
        self, storage: S3Storage, method_name: str
    ) -> None:
        """Test unsupported S3 operations raise NotImplementedError."""
        method = getattr(storage, method_name)
        with pytest.raises(NotImplementedError):
            method("key")

    def test_check_authorization_valid_succeeds(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test check_authorization validates bucket access."""
        storage.check_authorization()

        s3_client.put_object.assert_called_once()
        s3_client.delete_object.assert_called_once()

    def test_check_authorization_invalid_raises_when_no_client(
        self, backend: MagicMock
    ) -> None:
        """Test check_authorization fails when the client is unavailable."""
        backend.get_client.return_value = None
        instance = S3Storage(backend=backend, bucket_name="test-bucket")

        with pytest.raises(RuntimeError, match="Authentication failed"):
            instance.check_authorization()

    def test_check_authorization_invalid_raises_on_no_credentials(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test check_authorization maps missing credentials to RuntimeError."""
        s3_client.put_object.side_effect = NoCredentialsError()

        with pytest.raises(RuntimeError, match="AWS credentials"):
            storage.check_authorization()

    @pytest.mark.parametrize(
        "error_code",
        ["403", "AccessDenied"],
    )
    def test_check_authorization_invalid_raises_on_access_denied(
        self,
        storage: S3Storage,
        s3_client: MagicMock,
        error_code: str,
    ) -> None:
        """Test check_authorization maps access denied errors to RuntimeError."""
        s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": error_code, "Message": "Denied"}},
            "PutObject",
        )

        with pytest.raises(RuntimeError, match="permissions"):
            storage.check_authorization()

    def test_check_authorization_invalid_raises_on_unexpected_client_error(
        self, storage: S3Storage, s3_client: MagicMock
    ) -> None:
        """Test check_authorization wraps unexpected client errors."""
        s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Server error"}},
            "PutObject",
        )

        with pytest.raises(RuntimeError, match="Unexpected error"):
            storage.check_authorization()
