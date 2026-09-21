"""Tests for utils.bucket_storage.OCIObjectStorage."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from oci.exceptions import ServiceError

from utils.bucket_storage.OCIObjectStorage import OCIObjectStorage, chunks


def _make_oci(cluster_name="bundles", namespace="ns", bucket_name="test-bucket", region=None):
    """Build an OCIObjectStorage with a cached mock client and resolved namespace."""
    oci_store = OCIObjectStorage(
        auth_method="instance_principal",
        bucket_name=bucket_name,
        namespace=namespace,
        cluster_name=cluster_name,
        region=region,
    )
    mock_client = MagicMock()
    oci_store.object_storage_client = mock_client
    return oci_store, mock_client


def _list_objects_response(objects, next_start=None, prefixes=None):
    return SimpleNamespace(
        data=SimpleNamespace(
            objects=objects,
            prefixes=prefixes or [],
            next_start_with=next_start,
        )
    )


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


def test_init_defaults():
    oci_store = OCIObjectStorage(auth_method=None, bucket_name="b")
    assert oci_store.auth_method == "instance_principal"
    assert oci_store.region == "eu-paris-1"
    assert oci_store.namespace is None
    assert oci_store.cluster_name is None
    assert oci_store.object_storage_client is None


def test_init_honours_explicit_region():
    oci_store = OCIObjectStorage(
        auth_method="resource_principal", bucket_name="b", region="us-ashburn-1"
    )
    assert oci_store.auth_method == "resource_principal"
    assert oci_store.region == "us-ashburn-1"


@pytest.mark.parametrize(
    "cluster_name,key,expected",
    [
        (None, "file.json", "file.json"),
        ("bundles", "file.json", "bundles/file.json"),
    ],
)
def test_prefixed_key(cluster_name, key, expected):
    oci_store, _ = _make_oci(cluster_name=cluster_name)
    assert oci_store._prefixed_key(key) == expected


@pytest.mark.parametrize(
    "cluster_name,prefix,expected",
    [
        (None, "", ""),
        (None, "sub", "sub/"),
        ("bundles", "", "bundles/"),
        ("bundles", "sub", "bundles/sub/"),
    ],
)
def test_storage_prefix(cluster_name, prefix, expected):
    oci_store, _ = _make_oci(cluster_name=cluster_name)
    assert oci_store._storage_prefix(prefix) == expected


def test_logical_key_strips_cluster_prefix():
    oci_store, _ = _make_oci(cluster_name="bundles")
    assert oci_store._logical_key("bundles/file.json") == "file.json"
    assert oci_store._logical_key("other/file.json") == "other/file.json"


@pytest.mark.parametrize(
    "value,encoding,expected_body",
    [
        ("hello", "utf-8", b"hello"),
        (b"raw-bytes", "utf-8", b"raw-bytes"),
    ],
)
def test_set_uploads_prefixed_key(value, encoding, expected_body):
    oci_store, mock_client = _make_oci(cluster_name="bundles")
    oci_store.set("file.json", value, encoding=encoding)
    mock_client.put_object.assert_called_once_with(
        "ns", "test-bucket", "bundles/file.json", expected_body
    )


def test_set_aborts_when_client_unavailable():
    oci_store, _ = _make_oci()
    with patch.object(oci_store, "get_object_storage_client", return_value=None):
        oci_store.set("file.json", "data")  # should not raise


def test_get_returns_decoded_content():
    oci_store, mock_client = _make_oci(cluster_name="bundles")
    content = MagicMock()
    content.read.return_value = b"payload"
    mock_client.get_object.return_value = SimpleNamespace(
        data=SimpleNamespace(content=content)
    )
    assert oci_store.get("file.json") == "payload"
    mock_client.get_object.assert_called_once_with("ns", "test-bucket", "bundles/file.json")


def test_get_returns_none_on_missing_object():
    oci_store, mock_client = _make_oci()
    mock_client.get_object.side_effect = ServiceError(status=404)
    assert oci_store.get("missing.json") is None


def test_delete_removes_prefixed_object():
    oci_store, mock_client = _make_oci(cluster_name="bundles")
    oci_store.delete("file.json")
    mock_client.delete_object.assert_called_once_with(
        "ns", "test-bucket", "bundles/file.json"
    )


def test_list_yields_logical_keys():
    oci_store, mock_client = _make_oci(cluster_name="bundles")
    mock_client.list_objects.side_effect = [
        _list_objects_response(
            [SimpleNamespace(name="bundles/a.json"), SimpleNamespace(name="bundles/b.json")],
            next_start="tok",
        ),
        _list_objects_response([SimpleNamespace(name="bundles/c.json")]),
    ]
    assert list(oci_store.list()) == ["a.json", "b.json", "c.json"]


def test_list_with_last_modified_yields_keys_and_timestamps():
    oci_store, mock_client = _make_oci(cluster_name="bundles")
    ts1 = datetime(2026, 1, 1)
    ts2 = datetime(2026, 2, 2)
    mock_client.list_objects.return_value = _list_objects_response(
        [
            SimpleNamespace(name="bundles/a.json", time_modified=ts1),
            SimpleNamespace(name="bundles/b.json", time_modified=ts2),
        ]
    )
    assert list(oci_store.list_with_last_modified()) == [("a.json", ts1), ("b.json", ts2)]
    _, kwargs = mock_client.list_objects.call_args
    assert kwargs["fields"] == "name,timeModified"


def test_list_files_in_folder_delegates_to_list():
    oci_store, _ = _make_oci()
    with patch.object(oci_store, "list", return_value=iter(["a.json"])) as mock_list:
        assert list(oci_store.list_files_in_folder("sub")) == ["a.json"]
    mock_list.assert_called_once_with("sub")


def test_restore_soft_deleted_blob_not_implemented():
    oci_store, _ = _make_oci()
    with pytest.raises(NotImplementedError):
        oci_store.restore_soft_deleted_blob("file.json")
