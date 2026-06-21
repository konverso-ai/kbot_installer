"""Amazon S3 implementation of bucket storage."""

import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from backend.base import BackendBase
from backend.factory import create_backend
from botocore.exceptions import ClientError, NoCredentialsError
from more_itertools import chunked
from storage.base import StorageBase
from storage.download_utils import download_and_extract_tar_gz
from typing_extensions import override

log = logging.getLogger(__name__)


class S3Storage(StorageBase):
    """``StorageBase`` backend backed by Amazon S3."""

    name = "s3"
    _backend: BackendBase

    @override
    def get_name(self) -> str:
        """Return the name of the storage."""
        return self.name

    def __init__(
        self,
        bucket_name: str,
        cluster_name: str | None = None,
        region_name: str = "eu-west-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        backend: BackendBase | None = None,
    ) -> None:
        """Initialize S3 storage.

        Args:
            bucket_name: S3 bucket name.
            cluster_name: Optional root directory prefix inside the bucket.
            region_name: AWS region name.
            aws_access_key_id: AWS access key ID. Defaults to the environment.
            aws_secret_access_key: AWS secret access key. Defaults to the environment.
            backend: Pre-configured S3 backend. Used mainly in tests.

        """
        if backend is None:
            self._backend = create_backend(
                "s3",
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
        else:
            self._backend = backend
        self.bucket_name = bucket_name
        self.cluster_name = cluster_name
        log.debug(
            "Creating S3Storage(bucket_name='%s', cluster_name='%s')",
            self.bucket_name,
            self.cluster_name,
        )

    def _get_backend(self) -> BackendBase:
        """Return the backend used by this storage."""
        return self._backend

    def get_bucket_name(self) -> str | None:
        """Return the currently configured bucket name."""
        return self.bucket_name

    def set_bucket_name(self, bucket_name: str) -> None:
        """Switch the active bucket."""
        bucket_name = bucket_name.strip()
        if bucket_name:
            self.bucket_name = bucket_name

    def _prefixed_key(self, key: str) -> str:
        """Build the storage key used for single-object operations."""
        if self.cluster_name:
            return f"{self.cluster_name}/{key}"
        return key

    def _storage_prefix(self, prefix: str = "") -> str:
        """Build the storage prefix used for list and folder operations."""
        if self.cluster_name:
            storage_prefix = (
                f"{self.cluster_name}/{prefix}" if prefix else f"{self.cluster_name}/"
            )
        else:
            storage_prefix = prefix
        if storage_prefix and not storage_prefix.endswith("/"):
            storage_prefix += "/"
        return storage_prefix

    @override
    def set(self, key: str, value: str | bytes | Any, encoding: str = "utf-8") -> None:
        """Upload an object to AWS S3."""
        key = self._prefixed_key(key)
        s3_client = self._get_backend().get_client()
        if not s3_client:
            log.error("S3 client unavailable. Upload aborted.")
            return
        try:
            content = value.encode(encoding) if isinstance(value, str) else value
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
            )
            log.debug("Object '%s' uploaded successfully to AWS S3.", key)
        except Exception as e:
            log.error("Upload failed for '%s': %s", key, e, exc_info=True)

    @override
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve and decode an object from AWS S3."""
        key = self._prefixed_key(key)
        s3_client = self._get_backend().get_client()
        if not s3_client:
            log.error(
                "S3 client unavailable. Retrieval aborted. '%s'",
                self.bucket_name,
            )
            return None
        try:
            log.debug("BUCKET = %s :: %s", key, self.bucket_name)
            response = s3_client.get_object(Bucket=self.bucket_name, Key=key)
            data = response["Body"].read()
            log.debug(
                "Successfully retrieved object from AWS S3: %s; encoding: %s",
                key,
                encoding,
            )
            return data.decode(encoding)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                log.error("Path %s was not found in Bucket storage", key)
            else:
                log.error(
                    "Retrieval failed for key='%s'; encoding=%s: %s",
                    key,
                    encoding,
                    e,
                    exc_info=True,
                )
        except Exception as e:
            log.error(
                "Retrieval failed for key='%s'; encoding=%s: %s",
                key,
                encoding,
                e,
                exc_info=True,
            )
        return None

    @override
    def download(self, key: str, local_file_path: str) -> None:
        """Download a storage object to a local file or extract an archive to a directory."""
        path = Path(local_file_path)
        if path.is_dir():
            download_and_extract_tar_gz(self._download_file, key, path)
            return
        self._download_file(key, local_file_path)

    def _download_file(self, key: str, local_file_path: str) -> None:
        """Download a storage object to a local file."""
        key = self._prefixed_key(key)
        s3_client = self._get_backend().get_client()
        if not s3_client:
            log.error(
                "S3 client unavailable. Retrieval aborted. '%s'",
                self.bucket_name,
            )
            return

        with open(local_file_path, "wb") as local_file:
            s3_client.download_fileobj(self.bucket_name, key, local_file)

    @override
    def delete(self, key: str) -> None:
        """Delete a single object from AWS S3."""
        key = self._prefixed_key(key)
        s3_client = self._get_backend().get_client()
        if not s3_client:
            log.error("S3 client unavailable. Deletion aborted.")
            return
        try:
            s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            log.debug("Successfully deleted object from AWS S3: %s", key)
        except Exception as e:
            log.exception("Deletion failed for key='%s': %s", key, e)

    @override
    def delete_folder(self, key: str) -> None:
        """Delete all objects under a folder prefix."""
        s3_client = self._get_backend().get_client()
        if not s3_client:
            log.error("S3 client unavailable. Deletion aborted.")
            return

        try:
            prefix = self._storage_prefix(key)
            paginator = s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
            )

            deleted_count = 0
            for page in pages:
                if "Contents" not in page:
                    continue

                objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]
                if objects_to_delete:
                    for chunk in chunked(objects_to_delete, 1000):
                        s3_client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={"Objects": chunk},
                        )
                        deleted_count += len(chunk)

            if deleted_count == 0:
                log.debug("This key '%s' does not exist.", key)
            else:
                log.debug(
                    "The key '%s' contained '%d' elements. All were deleted.",
                    key,
                    deleted_count,
                )
        except Exception as e:
            log.error("Failed to delete folder '%s': %s", key, e, exc_info=True)

    @override
    def list(self, prefix: str = "") -> Iterator[str]:
        """List object keys under a logical prefix."""
        s3_client = self._get_backend().get_client()
        if not s3_client:
            log.error(
                "S3 client unavailable. Cannot list objects with prefix '%s'",
                prefix,
            )
            return

        try:
            storage_prefix = self._storage_prefix(prefix)
            cluster_prefix = f"{self.cluster_name}/" if self.cluster_name else ""
            paginator = s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=storage_prefix,
            )
            for page in pages:
                if "Contents" not in page:
                    continue
                for obj in page["Contents"]:
                    object_key = obj["Key"]
                    if cluster_prefix and object_key.startswith(cluster_prefix):
                        object_key = object_key[len(cluster_prefix):]
                    yield object_key

        except Exception as e:
            log.error(
                "Failed to list objects with prefix '%s': %s",
                prefix,
                e,
                exc_info=True,
            )

    @override
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List object keys contained in a folder."""
        yield from self.list(folder_path)

    @override
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path."""
        raise NotImplementedError

    @override
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restore a soft-deleted object."""
        raise NotImplementedError

    def check_authorization(self) -> None:
        """Validate AWS credentials and bucket access permissions."""
        s3_client = self._get_backend().get_client()
        if s3_client is None:
            raise RuntimeError(
                "Authentication failed. Ensure the AWS credentials and "
                "Bucket Information are correct."
            )

        try:
            start_time = time.time()
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key="temp_blob_for_checking",
                Body=b"Hi",
            )
            s3_client.delete_object(
                Bucket=self.bucket_name,
                Key="temp_blob_for_checking",
            )
            log.debug(
                "Authorization check passed. Connected to AWS S3 in duration %.3f(s)",
                time.time() - start_time,
            )
        except NoCredentialsError as e:
            log.error(
                "Authentication failed. Check the AWS credentials. Error: %s",
                e,
                exc_info=True,
            )
            raise RuntimeError(
                "Authentication failed. Ensure the AWS credentials are correct."
            ) from e
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in {"403", "AccessDenied"}:
                log.error(
                    "Authentication failed. Check the AWS credentials and permissions. Error: %s",
                    e,
                    exc_info=True,
                )
                raise RuntimeError(
                    "Authentication failed. Ensure the AWS credentials and "
                    "permissions are correct."
                ) from e
            log.error(
                "Unexpected error during authorization check. Error: %s",
                e,
                exc_info=True,
            )
            raise RuntimeError("Unexpected error during authorization check") from e
        except Exception as e:
            log.error(
                "Unexpected error during authorization check. Error: %s",
                e,
                exc_info=True,
            )
            raise RuntimeError("Unexpected error during authorization check") from e
