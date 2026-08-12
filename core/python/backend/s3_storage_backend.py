"""AWS S3 authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from utils.Logger import logger

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

    from credentials.s3_credentials import S3Credentials

log = logger.get_package_logger("backend")


class S3StorageBackend:
    """Backend for AWS S3."""

    _client: S3Client | None

    def __init__(self, credentials: S3Credentials) -> None:
        """Build the boto3 S3 client from the given credentials.

        Args:
            credentials: AWS connection config used to configure the underlying
                boto3 client. Authentication itself is resolved by boto3's own
                default credential chain.

        """
        self.__credentials = credentials
        self.__client = boto3.client(
            "s3",
            region_name=self.__credentials.region_name,
            endpoint_url=self.__credentials.endpoint_url,
            config=Config(
                max_pool_connections=self.__credentials.max_pool_connections,
                retries={
                    "mode": "standard",
                    "max_attempts": self.__credentials.retry_max_attempts,
                },
            ),
        )

    def get_client(self) -> S3Client:
        """Return the S3 client."""
        return self.__client
