"""AWS S3 authentication and client management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from credentials.s3_credentials import S3Credentials

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

log = logging.getLogger(__name__)


class S3Backend:
    """Backend for AWS S3."""

    _client: S3Client | None

    def __init__(self, settings: S3Credentials) -> None:
        """Build the boto3 S3 client from the given credentials.

        Args:
            settings: AWS credentials and connection settings used to configure
                the underlying boto3 client.

        """
        self.__settings = settings
        self.__client = boto3.client(
            "s3",
            region_name=self.__settings.region_name,
            aws_access_key_id=self.__settings.access_key_id,
            aws_secret_access_key=self.__settings.secret_access_key,
            aws_session_token=self.__settings.session_token,
            endpoint_url=self.__settings.endpoint_url,
            config=Config(
                max_pool_connections=self.__settings.max_pool_connections,
                retries={
                    "mode": "standard",
                    "max_attempts": self.__settings.retry_max_attempts,
                },
            ),
        )

    def get_client(self) -> S3Client:
        """Return the S3 client."""
        return self.__client
