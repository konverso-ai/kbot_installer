"""Tests for s3_backend module."""

from unittest.mock import MagicMock, patch

from pytest import MonkeyPatch

from backend.s3_backend import S3Backend
from credentials.s3_credentials import S3Credentials
from utils.utils_for_unit_tests import compare


class TestS3Backend:
    """Test cases for S3Backend class."""

    def test_init_valid_builds_client_from_credentials(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test S3Backend builds a boto3 S3 client from the given credentials."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-3")
        with patch("backend.s3_backend.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            credentials = S3Credentials(
                max_pool_connections=5,
                retry_max_attempts=2,
            )

            backend = S3Backend(credentials)

            mock_boto3.client.assert_called_once()
            args, kwargs = mock_boto3.client.call_args
            assert compare("eq", args[0], "s3")
            assert compare("eq", kwargs["region_name"], "eu-west-3")
            assert kwargs["endpoint_url"] is None
            assert compare("eq", backend.get_client(), mock_client)
