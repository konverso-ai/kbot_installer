"""Tests for utils.bucket_storage.AmazonS3."""
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from utils.bucket_storage.AmazonS3 import AmazonS3, chunks


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
    "config_overrides,expected_region,expected_bucket,expected_cluster",
    [
        ({}, "us-east-1", "test-bucket", "test-cluster"),
        ({"aws_s3_region": None}, "us-east-1", "test-bucket", "test-cluster"),
        ({"aws_s3_region": "eu-west-1"}, "eu-west-1", "test-bucket", "test-cluster"),
        ({"aws_s3_bucket_name": "other-bucket"}, "us-east-1", "other-bucket", "test-cluster"),
    ],
)
def test_init_reads_bot_config(
    mock_bot_config, config_overrides, expected_region, expected_bucket, expected_cluster
):
    config, _ = mock_bot_config
    config.update(config_overrides)

    s3 = AmazonS3()

    assert s3.region_name == expected_region
    assert s3.bucket_name == expected_bucket
    assert s3.cluster_name == expected_cluster
    assert s3.s3_client is None


@pytest.mark.parametrize("bucket_name", ["", None])
def test_connect_returns_none_when_bucket_not_configured(mock_bot_config, bucket_name):
    config, _ = mock_bot_config
    config["aws_s3_bucket_name"] = bucket_name

    s3 = AmazonS3()

    assert s3._get_s3_client(bucket_name=s3.bucket_name) is None


@pytest.mark.parametrize(
    "access_key,secret_key,uses_explicit_credentials",
    [
        ("AKIA123", "secret", True),
        (None, None, False),
        ("AKIA123", None, False),
        (None, "secret", False),
    ],
)
def test_connect_uses_credentials_when_both_provided(
    mock_bot_config, access_key, secret_key, uses_explicit_credentials
):
    config, _ = mock_bot_config
    config["aws_s3_access_key_id"] = access_key
    config["aws_s3_secret_access_key"] = secret_key

    mock_client = MagicMock()
    with patch("utils.bucket_storage.AmazonS3.boto3.client", return_value=mock_client) as mock_boto:
        s3 = AmazonS3()
        result = s3._get_s3_client(bucket_name="test-bucket")

    assert result is mock_client
    kwargs = mock_boto.call_args.kwargs
    if uses_explicit_credentials:
        assert kwargs["aws_access_key_id"] == access_key
        assert kwargs["aws_secret_access_key"] == secret_key
    else:
        assert "aws_access_key_id" not in kwargs
        assert "aws_secret_access_key" not in kwargs


@pytest.mark.parametrize(
    "exception,expected_client",
    [
        (NoCredentialsError(), None),
        (RuntimeError("boom"), None),
    ],
)
def test_connect_handles_connection_errors(mock_bot_config, exception, expected_client):
    with patch("utils.bucket_storage.AmazonS3.boto3.client", side_effect=exception):
        s3 = AmazonS3()
        assert s3._get_s3_client(bucket_name="test-bucket") is expected_client


@pytest.mark.parametrize(
    "region,should_set_location",
    [
        ("us-east-1", False),
        ("eu-west-1", True),
    ],
)
def test_create_bucket_on_404(mock_bot_config, region, should_set_location):
    config, _ = mock_bot_config
    config["aws_s3_region"] = region

    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadBucket"
    )

    s3 = AmazonS3()
    s3.create_bucket(mock_client)

    if should_set_location:
        mock_client.create_bucket.assert_called_once_with(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    else:
        mock_client.create_bucket.assert_called_once_with(Bucket="test-bucket")


def test_create_bucket_skips_when_bucket_exists(mock_bot_config):
    mock_client = MagicMock()

    AmazonS3().create_bucket(mock_client)

    mock_client.create_bucket.assert_not_called()


@pytest.mark.parametrize("bucket_name,should_update", [("", False), ("   ", False), ("new-bucket", True)])
def test_set_bucket_name(mock_bot_config, bucket_name, should_update):
    s3 = AmazonS3()
    mock_client = MagicMock()
    s3.s3_client = mock_client

    with patch.object(s3, "_get_s3_client", return_value=mock_client) as mock_get:
        s3.set_bucket_name(bucket_name)

    if should_update:
        mock_get.assert_called_once_with(bucket_name="new-bucket")
        assert s3.bucket_name == "new-bucket"
    else:
        mock_get.assert_not_called()


@pytest.mark.parametrize(
    "value,encoding,expected_body",
    [
        ("hello", "utf-8", b"hello"),
        ("café", "utf-8", "café".encode("utf-8")),
        (b"raw-bytes", "utf-8", b"raw-bytes"),
    ],
)
def test_set_uploads_prefixed_key(mock_bot_config, value, encoding, expected_body):
    s3 = AmazonS3()
    mock_client = MagicMock()
    s3.s3_client = mock_client

    s3.set("path/file.txt", value, encoding=encoding)

    mock_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test-cluster/path/file.txt",
        Body=expected_body,
    )


def test_set_aborts_when_client_unavailable(mock_bot_config):
    s3 = AmazonS3()

    with patch.object(s3, "get_s3_client", return_value=None):
        s3.set("file.txt", "data")

    assert s3.s3_client is None


@pytest.mark.parametrize(
    "body,encoding,expected",
    [
        (b"hello", "utf-8", "hello"),
        ("café".encode("latin-1"), "latin-1", "café"),
    ],
)
def test_get_returns_decoded_content(mock_bot_config, body, encoding, expected):
    s3 = AmazonS3()
    mock_client = MagicMock()
    mock_client.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=body))}
    s3.s3_client = mock_client

    result = s3.get("path/file.txt", encoding=encoding)

    assert result == expected
    mock_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test-cluster/path/file.txt",
    )


@pytest.mark.parametrize(
    "error_code,expected_result",
    [
        ("NoSuchKey", None),
        ("AccessDenied", None),
    ],
)
def test_get_handles_client_errors(mock_bot_config, error_code, expected_result):
    s3 = AmazonS3()
    mock_client = MagicMock()
    mock_client.get_object.side_effect = ClientError(
        {"Error": {"Code": error_code}}, "GetObject"
    )
    s3.s3_client = mock_client

    assert s3.get("missing.txt") == expected_result


def test_get_returns_none_when_client_unavailable(mock_bot_config):
    s3 = AmazonS3()

    with patch.object(s3, "get_s3_client", return_value=None):
        assert s3.get("file.txt") is None


def test_delete_removes_prefixed_object(mock_bot_config):
    s3 = AmazonS3()
    mock_client = MagicMock()
    s3.s3_client = mock_client

    s3.delete("path/file.txt")

    mock_client.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test-cluster/path/file.txt",
    )


@pytest.mark.parametrize(
    "prefix,expected_storage_prefix,expected_keys",
    [
        ("", "test-cluster/", ["a.txt", "b.txt"]),
        ("folder", "test-cluster/folder/", ["folder/a.txt", "folder/b.txt"]),
        ("folder/", "test-cluster/folder/", ["folder/a.txt", "folder/b.txt"]),
    ],
)
def test_list_normalizes_prefix_and_yields_keys(
    mock_bot_config, prefix, expected_storage_prefix, expected_keys
):
    s3 = AmazonS3()
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {"Key": f"{expected_storage_prefix}a.txt"},
                {"Key": f"{expected_storage_prefix}b.txt"},
            ]
        },
        {},
    ]
    s3.s3_client = mock_client

    assert list(s3.list(prefix)) == expected_keys
    mock_paginator.paginate.assert_called_once_with(
        Bucket="test-bucket",
        Prefix=expected_storage_prefix,
    )


def test_list_returns_empty_list_on_error(mock_bot_config):
    s3 = AmazonS3()
    mock_client = MagicMock()
    mock_client.get_paginator.side_effect = RuntimeError("list failed")
    s3.s3_client = mock_client

    assert list(s3.list("folder")) == []


@pytest.mark.parametrize("folder_path", ["", "docs", "docs/"])
def test_list_files_in_folder_delegates_to_list(mock_bot_config, folder_path):
    s3 = AmazonS3()
    expected = [f"{folder_path or ''}file.txt"]

    with patch.object(s3, "list", return_value=iter(expected)) as mock_list:
        assert list(s3.list_files_in_folder(folder_path)) == expected
        mock_list.assert_called_once_with(folder_path)


def test_delete_folder_batches_deletions(mock_bot_config):
    s3 = AmazonS3()
    mock_client = MagicMock()
    mock_paginator = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = [
        {"Contents": [{"Key": f"test-cluster/folder/file{i}.txt"} for i in range(3)]},
    ]
    s3.s3_client = mock_client

    s3.delete_folder("folder")

    mock_paginator.paginate.assert_called_once_with(
        Bucket="test-bucket",
        Prefix="test-cluster/folder/",
    )
    mock_client.delete_objects.assert_called_once()
    deleted_keys = mock_client.delete_objects.call_args.kwargs["Delete"]["Objects"]
    assert len(deleted_keys) == 3


@pytest.mark.parametrize("method_name", ["list_folders", "restore_soft_deleted_blob"])
def test_unimplemented_methods_raise(mock_bot_config, method_name):
    s3 = AmazonS3()

    with pytest.raises(NotImplementedError):
        getattr(s3, method_name)("key")


@pytest.mark.parametrize(
    "error,expected_message",
    [
        (NoCredentialsError(), "Ensure the AWS credentials are correct"),
        (
            ClientError({"Error": {"Code": "403"}}, "PutObject"),
            "Ensure the AWS credentials and permissions are correct",
        ),
        (
            ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject"),
            "Ensure the AWS credentials and permissions are correct",
        ),
        (RuntimeError("boom"), "Unexpected error during authorization check"),
    ],
)
def test_check_authorization_raises_on_failure(mock_bot_config, error, expected_message):
    s3 = AmazonS3()
    mock_client = MagicMock()
    mock_client.put_object.side_effect = error
    s3.s3_client = mock_client

    with pytest.raises(RuntimeError, match=expected_message):
        s3.check_authorization()


def test_check_authorization_succeeds_with_temp_object(mock_bot_config):
    s3 = AmazonS3()
    mock_client = MagicMock()
    s3.s3_client = mock_client

    s3.check_authorization()

    mock_client.put_object.assert_called_once()
    mock_client.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="temp_blob_for_checking",
    )
