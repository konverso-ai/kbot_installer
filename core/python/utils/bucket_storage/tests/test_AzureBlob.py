"""Tests for utils.bucket_storage.AzureBlob."""
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError, ResourceExistsError, ResourceNotFoundError

from azure.storage.blob import BlobPrefix

from utils.bucket_storage.AzureBlob import AzureBlob, chunks


@pytest.mark.parametrize(
    "iterable,chunk_size,expected",
    [
        ([], 3, []),
        ([1, 2, 3], 10, [[1, 2, 3]]),
        (range(5), 2, [[0, 1], [2, 3], [4]]),
        (range(6), 3, [[0, 1, 2], [3, 4, 5]]),
        ("abcdef", 2, [["a", "b"], ["c", "d"], ["e", "f"]]),
    ],
)
def test_chunks(iterable, chunk_size, expected):
    assert list(chunks(iterable, chunk_size)) == expected


@pytest.mark.parametrize(
    "account_url,container_name,expected_account,expected_container",
    [
        (None, None, "https://testaccount.blob.core.windows.net", "test-container"),
        ("https://custom.blob.core.windows.net", "custom-container", "https://custom.blob.core.windows.net", "custom-container"),
        ("https://custom.blob.core.windows.net", None, "https://custom.blob.core.windows.net", "test-container"),
    ],
)
def test_init_uses_constructor_or_bot_config(
    mock_bot_config, account_url, container_name, expected_account, expected_container
):
    blob = AzureBlob(account_url=account_url, container_name=container_name)

    assert blob.account_url == expected_account
    assert blob.container_name == expected_container
    assert blob.container_client is None


@pytest.mark.parametrize("account_url", ["", None])
def test_connect_returns_none_when_account_url_missing(mock_bot_config, account_url):
    config, _ = mock_bot_config
    config["kbot_storage_account"] = account_url

    blob = AzureBlob()

    assert blob._get_container_client(container_name="test-container") is None


def test_connect_returns_service_client_on_success(mock_bot_config):
    mock_container = MagicMock()
    mock_service = MagicMock()
    mock_service.get_container_client.return_value = mock_container

    with patch(
        "utils.bucket_storage.AzureBlob.BlobServiceClient",
        return_value=mock_service,
    ), patch(
        "utils.bucket_storage.AzureBlob.DefaultAzureCredential",
        return_value=MagicMock(),
    ):
        blob = AzureBlob()
        result = blob._get_container_client(container_name="test-container")

    assert result is mock_container
    mock_service.get_container_client.assert_called_with("test-container")


@pytest.mark.parametrize(
    "exception,expected_client",
    [
        (ResourceNotFoundError("missing"), None),
        (RuntimeError("boom"), None),
    ],
)
def test_connect_handles_connection_errors(mock_bot_config, exception, expected_client):
    with patch(
        "utils.bucket_storage.AzureBlob.BlobServiceClient",
        side_effect=exception,
    ), patch(
        "utils.bucket_storage.AzureBlob.DefaultAzureCredential",
        return_value=MagicMock(),
    ):
        blob = AzureBlob()
        assert blob._get_container_client(container_name="test-container") is expected_client


def test_create_container_ignores_existing_container(mock_bot_config):
    mock_service = MagicMock()
    mock_service.create_container.side_effect = ResourceExistsError("exists")

    AzureBlob().create_container(mock_service)

    mock_service.create_container.assert_called_once_with(name="test-container")


@pytest.mark.parametrize("container_name,should_update", [("", False), ("   ", False), ("new-container", True)])
def test_set_container_name(mock_bot_config, container_name, should_update):
    blob = AzureBlob()
    mock_container = MagicMock()
    blob.container_client = mock_container

    with patch.object(blob, "_get_container_client", return_value=mock_container) as mock_get:
        blob.set_container_name(container_name)

    if should_update:
        mock_get.assert_called_once_with(container_name="new-container")
        assert blob.container_name == "new-container"
    else:
        mock_get.assert_not_called()


@pytest.mark.parametrize(
    "value,encoding,expected_content",
    [
        ("hello", "utf-8", b"hello"),
        ("café", "utf-8", "café".encode("utf-8")),
        (b"raw-bytes", "utf-8", b"raw-bytes"),
    ],
)
def test_set_uploads_blob(mock_bot_config, value, encoding, expected_content):
    blob = AzureBlob()
    mock_container = MagicMock()
    blob.container_client = mock_container

    blob.set("path/file.txt", value, encoding=encoding)

    mock_container.upload_blob.assert_called_once_with(
        name="path/file.txt",
        data=expected_content,
        overwrite=True,
    )


def test_set_aborts_when_client_unavailable(mock_bot_config):
    blob = AzureBlob()

    with patch.object(blob, "get_container_client", return_value=None):
        blob.set("file.txt", "data")

    assert blob.container_client is None


@pytest.mark.parametrize(
    "body,encoding,expected",
    [
        (b"hello", "utf-8", "hello"),
        ("café".encode("latin-1"), "latin-1", "café"),
    ],
)
def test_get_returns_decoded_content(mock_bot_config, body, encoding, expected):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_blob_client = MagicMock()
    mock_blob_client.download_blob.return_value.readall.return_value = body
    mock_container.get_blob_client.return_value = mock_blob_client
    blob.container_client = mock_container

    result = blob.get("path/file.txt", encoding=encoding)

    assert result == expected
    mock_container.get_blob_client.assert_called_once_with("path/file.txt")


def test_get_returns_none_on_resource_not_found(mock_bot_config):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_container.get_blob_client.return_value.download_blob.side_effect = ResourceNotFoundError(
        "missing"
    )
    blob.container_client = mock_container

    assert blob.get("missing.txt") is None


def test_delete_removes_blob(mock_bot_config):
    blob = AzureBlob()
    mock_container = MagicMock()
    blob.container_client = mock_container

    blob.delete("path/file.txt")

    mock_container.delete_blob.assert_called_once_with("path/file.txt")


@pytest.mark.parametrize(
    "prefix,expected_prefix",
    [
        ("", ""),
        ("folder", "folder/"),
        ("folder/", "folder/"),
    ],
)
def test_list_normalizes_prefix_and_yields_blob_names(mock_bot_config, prefix, expected_prefix):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_blob_a = MagicMock(name="blob-a")
    mock_blob_a.name = f"{expected_prefix}a.txt"
    mock_blob_b = MagicMock(name="blob-b")
    mock_blob_b.name = f"{expected_prefix}b.txt"
    mock_container.list_blobs.return_value = [mock_blob_a, mock_blob_b]
    blob.container_client = mock_container

    assert list(blob.list(prefix)) == [f"{expected_prefix}a.txt", f"{expected_prefix}b.txt"]
    mock_container.list_blobs.assert_called_once_with(name_starts_with=expected_prefix)


@pytest.mark.parametrize("folder_path", ["", "docs", "docs/"])
def test_list_files_in_folder_delegates_to_list(mock_bot_config, folder_path):
    blob = AzureBlob()
    expected = [f"{folder_path or ''}file.txt"]

    with patch.object(blob, "list", return_value=iter(expected)) as mock_list:
        assert list(blob.list_files_in_folder(folder_path)) == expected
        mock_list.assert_called_once_with(folder_path)


@pytest.mark.parametrize(
    "path,expected_path,folder_prefixes,expected_folders",
    [
        ("", "", ["docs/", "images/"], ["docs", "images"]),
        ("root", "root/", ["root/sub/"], ["sub"]),
        ("root/", "root/", ["root/sub/"], ["sub"]),
    ],
)
def test_list_folders_yields_folder_names(
    mock_bot_config, path, expected_path, folder_prefixes, expected_folders
):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_container.walk_blobs.return_value = [
        BlobPrefix(prefix=prefix) for prefix in folder_prefixes
    ]
    blob.container_client = mock_container

    assert list(blob.list_folders(path)) == expected_folders
    mock_container.walk_blobs.assert_called_once_with(name_starts_with=expected_path, delimiter="/")


def test_delete_folder_deletes_blobs_in_chunks(mock_bot_config):
    blob = AzureBlob()
    mock_container = MagicMock()

    class NamedBlob:
        def __init__(self, name):
            self.name = name

    mock_container.list_blobs.return_value = [
        NamedBlob("folder/a.txt"),
        NamedBlob("folder/b.txt"),
    ]
    blob.container_client = mock_container

    blob.delete_folder("folder")

    mock_container.delete_blobs.assert_called_once_with("folder/a.txt", "folder/b.txt")


def test_delete_folder_noop_when_prefix_empty(mock_bot_config):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_container.list_blobs.return_value = []
    blob.container_client = mock_container

    blob.delete_folder("missing")

    mock_container.delete_blobs.assert_not_called()


@pytest.mark.parametrize(
    "deleted,undelete_result,expected",
    [
        (False, False, True),
        (True, False, True),
        (True, True, False),
    ],
)
def test_restore_soft_deleted_blob(mock_bot_config, deleted, undelete_result, expected):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_blob_client = MagicMock()
    mock_blob_client.get_blob_properties.return_value.deleted = deleted
    mock_container.get_blob_client.return_value = mock_blob_client
    blob.container_client = mock_container

    if deleted:
        mock_blob_client.get_blob_properties.side_effect = [
            MagicMock(deleted=True),
            MagicMock(deleted=undelete_result),
        ]

    assert blob.restore_soft_deleted_blob("file.txt") is expected


@pytest.mark.parametrize(
    "exception,expected",
    [
        (ResourceNotFoundError("missing"), False),
        (RuntimeError("boom"), False),
    ],
)
def test_restore_soft_deleted_blob_returns_false_on_error(
    mock_bot_config, exception, expected
):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_blob_client = MagicMock()
    mock_blob_client.get_blob_properties.side_effect = RuntimeError("props failed")
    mock_blob_client.undelete_blob.side_effect = exception
    mock_container.get_blob_client.return_value = mock_blob_client
    blob.container_client = mock_container

    assert blob.restore_soft_deleted_blob("file.txt") is expected


def test_restore_soft_deleted_blob_returns_false_without_client(mock_bot_config):
    blob = AzureBlob()

    with patch.object(blob, "get_container_client", return_value=None):
        assert blob.restore_soft_deleted_blob("file.txt") is False


def test_restore_soft_deleted_blob_returns_false_when_blob_client_unavailable(mock_bot_config):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_container.get_blob_client.side_effect = RuntimeError("client failed")
    blob.container_client = mock_container

    assert blob.restore_soft_deleted_blob("file.txt") is False


@pytest.mark.parametrize(
    "error,expected_message",
    [
        (ClientAuthenticationError("auth"), "Ensure the SAS token and Authorization header are correct"),
        (RuntimeError("boom"), "Unexpected error during authorization check"),
    ],
)
def test_check_authorization_raises_on_failure(mock_bot_config, error, expected_message):
    blob = AzureBlob()
    mock_container = MagicMock()
    mock_container.upload_blob.side_effect = error
    blob.container_client = mock_container

    with pytest.raises(RuntimeError, match=expected_message):
        blob.check_authorization()


def test_check_authorization_succeeds_with_temp_blob(mock_bot_config):
    blob = AzureBlob()
    mock_container = MagicMock()
    blob.container_client = mock_container

    blob.check_authorization()

    mock_container.upload_blob.assert_called_once_with(
        name="temp_blob_for_checking",
        data=b"Hi",
        overwrite=True,
    )
    mock_container.delete_blob.assert_called_once_with("temp_blob_for_checking")
