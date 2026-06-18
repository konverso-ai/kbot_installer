"""AWS S3 authentication and client management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any

import boto3
from backend.base import BackendBase
from botocore.config import Config
from pydantic import ConfigDict, Field, PrivateAttr
from typing_extensions import override

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

log = logging.getLogger(__name__)


class S3Backend(BackendBase):
    """Backend for AWS S3."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    region_name: Annotated[str, Field(default="eu-west-1")]
    aws_access_key_id: Annotated[str | None, Field(default=None)]
    aws_secret_access_key: Annotated[str | None, Field(default=None)]
    aws_session_token: Annotated[str | None, Field(default=None)]
    endpoint_url: Annotated[str | None, Field(default=None)]

    max_pool_connections: Annotated[int, Field(default=10, ge=1)]
    retry_max_attempts: Annotated[int, Field(default=3, ge=1)]

    _client: S3Client | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any, __config: Any) -> None:
        """Initialize the S3 backend."""
        self._client = boto3.client(
            "s3",
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            endpoint_url=self.endpoint_url,
            config=Config(
                max_pool_connections=self.max_pool_connections,
                retries={
                    "mode": "standard",
                    "max_attempts": self.retry_max_attempts,
                },
            ),
        )

    @override
    def get_client(self) -> S3Client:
        """Return the S3 client."""
        return self._client
