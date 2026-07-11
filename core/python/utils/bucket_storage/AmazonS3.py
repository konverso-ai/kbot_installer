"""Amazon S3 implementation of bucket storage."""

import itertools
import time
from typing import Any
from collections.abc import Iterator

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing_extensions import override

from utils.Logger import logger
from utils.bucket_storage.base import BucketStorage

log = logger.getPackageLogger("bucket_storage")


def chunks(iterable, n: int) -> Iterator[list[Any]]:
    """Split an iterable into fixed-size chunks.

    Args:
        iterable: Source iterable to split.
        n: Maximum number of items per chunk.

    Yields:
        Lists containing up to ``n`` items from ``iterable``.

    """
    iterator = iter(iterable)
    while True:
        chunk = list(itertools.islice(iterator, n))
        if not chunk:
            break
        yield chunk


class AmazonS3(BucketStorage):
    """``BucketStorage`` backend backed by Amazon S3."""

    # No name, such that this class will not be loaded in factory
    name = ""

    def __init__(self, region_name=None, bucket_name=None, cluster_name=None) -> None:
        """Initialize S3 settings from the bot configuration."""
        from Bot import Bot  # pylint: disable=import-error

        config = Bot()
        if region_name is None:
            region_name = config.GetConfig("aws_s3_region") or "us-east-1"
        if bucket_name is None:
            bucket_name = config.GetConfig("aws_s3_bucket_name")
        if cluster_name is None:
            cluster_name = config.GetConfig("cluster_name")
        self.region_name = region_name
        self.bucket_name = bucket_name

        # Optional root directory
        self.cluster_name = cluster_name
        self.s3_client = None
        log.debug(
            "Creating AmazonS3(region='%s', bucket_name='%s')",
            self.region_name,
            self.bucket_name,
        )

    def __connect_to_s3_service(self):
        """Create and cache a boto3 S3 client.

        Uses explicit credentials from configuration when available, otherwise
        falls back to the default AWS credential chain.

        Returns:
            A connected S3 client, or ``None`` if the bucket is not configured
            or the connection fails.

        """
        if not self.bucket_name:
            log.warning("S3 bucket name '%s' is not configured.", self.bucket_name)
            return None
        try:
            from Bot import Bot  # pylint: disable=import-error

            config = Bot()
            aws_access_key_id = config.GetConfig("aws_s3_access_key_id")
            aws_secret_access_key = config.GetConfig("aws_s3_secret_access_key")

            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    "s3",
                    region_name=self.region_name,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
            else:
                self.s3_client = boto3.client("s3", region_name=self.region_name)

            self.create_bucket(self.s3_client)
            log.info(
                "Successfully connected to AWS S3 for bucket: %s", self.bucket_name
            )
            return self.s3_client
        except NoCredentialsError:
            log.warning(
                "AWS credentials not found for S3 bucket '%s'.", self.bucket_name
            )
            return None
        except Exception as e:
            log.error("Failed to connect to AWS S3. Error: %s", e, exc_info=True)
            return None

    def create_bucket(self, s3_client) -> None:
        """Create the configured bucket when it does not already exist.

        Args:
            s3_client: Connected boto3 S3 client.

        """
        try:
            s3_client.head_bucket(Bucket=self.bucket_name)
            log.fine("S3 Bucket %s already exists", self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                try:
                    if self.region_name == "us-east-1":
                        s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                "LocationConstraint": self.region_name
                            },
                        )
                    log.info("Created S3 Bucket %s", self.bucket_name)
                except Exception as create_error:
                    log.error(
                        "Couldn't create S3 Bucket %s due to %s",
                        self.bucket_name,
                        str(create_error),
                    )
            else:
                log.error(
                    "Couldn't access S3 Bucket %s due to %s", self.bucket_name, str(e)
                )
        except Exception as e:
            log.error(
                "Couldn't create S3 Bucket %s due to %s", self.bucket_name, str(e)
            )

    def get_bucket_name(self) -> str | None:
        """Return the currently configured bucket name.

        Returns:
            The active S3 bucket name.

        """
        return self.bucket_name

    def set_bucket_name(self, bucket_name: str) -> None:
        """Switch the active bucket after validating connectivity.

        Args:
            bucket_name: New bucket name to use.

        """
        bucket_name = bucket_name.strip()
        if not bucket_name:
            log.warning("Cannot update the bucket with nothing input information.")
            return
        s3_client = self._get_s3_client(bucket_name=bucket_name)
        if s3_client is None:
            log.warning(
                "Cannot update bucket information. Please review bucket name: %s",
                bucket_name,
            )
            return
        log.info("Update S3 client and related information.")
        self.bucket_name = bucket_name
        self.s3_client = s3_client

    def _get_s3_client(self, bucket_name: str):
        """Return an S3 client connected to a specific bucket.

        Args:
            bucket_name: Bucket name to validate and connect to.

        Returns:
            A connected S3 client, or ``None`` if initialization fails.

        """
        service_client = self.__connect_to_s3_service()
        if service_client:
            try:
                service_client.head_bucket(Bucket=bucket_name)
                self.s3_client = service_client
                log.info("Connected to AWS S3 bucket '%s'.", bucket_name)
                return self.s3_client
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "404":
                    log.warning("Bucket '%s' does not exist.", bucket_name)
                else:
                    log.error(
                        "Failed to access bucket '%s'. Error: %s",
                        bucket_name,
                        e,
                        exc_info=True,
                    )
                return None
            except Exception as e:
                log.error("Failed to connect to S3 bucket. Error: %s", e, exc_info=True)
                return None
        log.error("S3 client initialization failed.")
        return None

    def get_s3_client(self):
        """Return the cached S3 client, initializing it when needed.

        Returns:
            A connected S3 client, or ``None`` if initialization fails.

        """
        if self.s3_client:
            return self.s3_client
        if not self.bucket_name:
            return None
        return self._get_s3_client(bucket_name=self.bucket_name)

    def _prefixed_key(self, key: str) -> str:
        """Build the storage key used for single-object operations.

        Args:
            key: Logical object key provided by callers.

        Returns:
            The key prefixed with ``cluster_name`` when configured.

        """
        if self.cluster_name:
            return f"{self.cluster_name}/{key}"
        return key

    def _storage_prefix(self, prefix: str = "") -> str:
        """Build the storage prefix used for list and folder operations.

        Args:
            prefix: Logical prefix provided by callers.

        Returns:
            The prefix scoped to ``cluster_name`` and normalized with a
            trailing slash when not empty.

        """
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
    def set(
        self,
        key: str,
        value: str | bytes | Any,
        encoding: str = "utf-8",
        raise_on_status=False,
    ) -> None:
        """Upload an object to AWS S3.

        Args:
            key: Logical object key.
            value: Object content. Strings are encoded before upload.
            encoding: Character encoding used when ``value`` is a string.

        """
        key = self._prefixed_key(key)

        s3_client = self.get_s3_client()
        if not s3_client:
            log.error("S3 client unavailable. Upload aborted.")
            return
        try:
            content = value.encode(encoding) if isinstance(value, str) else value
            s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=content)
            log.debug("Object '%s' uploaded successfully to AWS S3.", key)
        except Exception as e:
            log.error("Upload failed for '%s': %s", key, e, exc_info=True)
            if raise_on_status:
                raise

    @override
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve and decode an object from AWS S3.

        Args:
            key: Logical object key.
            encoding: Character encoding used to decode the object content.

        Returns:
            The decoded object content, or ``None`` if retrieval fails.

        """
        key = self._prefixed_key(key)

        s3_client = self.get_s3_client()
        if not s3_client:
            log.error(
                "S3 client unavailable. Retrieval aborted. '%s'", self.bucket_name
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
    def download(self, key: str, local_file_path: str):
        """Download a storageobject to a local file

        Args:
            key: Destination object key.
            local_file_path: Local path to the file to be created

        """
        key = self._prefixed_key(key)

        s3_client = self.get_s3_client()
        if not s3_client:
            log.error(
                "S3 client unavailable. Retrieval aborted. '%s'", self.bucket_name
            )
            return None

        with open(local_file_path, "wb") as local_file:
            s3_client.download_fileobj(self.bucket_name, key, local_file)

    @override
    def delete(self, key: str) -> None:
        """Delete a single object from AWS S3.

        Args:
            key: Logical object key.

        """
        key = self._prefixed_key(key)

        s3_client = self.get_s3_client()
        if not s3_client:
            log.error("S3 client unavailable. Deletion aborted.")
            return None
        try:
            s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            log.debug("Successfully deleted object from AWS S3: %s", key)
        except Exception as e:
            log.exception("Deletion failed for key='%s': %s", key, e)
        return None

    @override
    def delete_folder(self, key: str) -> None:
        """Delete all objects under a folder prefix.

        Args:
            key: Logical folder prefix to delete.

        """
        s3_client = self.get_s3_client()
        if not s3_client:
            log.error("S3 client unavailable. Deletion aborted.")
            return

        try:
            prefix = self._storage_prefix(key)
            paginator = s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            i = 0
            for page in pages:
                if "Contents" not in page:
                    continue

                objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]
                if objects_to_delete:
                    for chunk in chunks(objects_to_delete, 1000):
                        s3_client.delete_objects(
                            Bucket=self.bucket_name, Delete={"Objects": chunk}
                        )
                        i += len(chunk)

            if i == 0:
                log.debug("This key '%s' does not exist.", key)
            else:
                log.debug(
                    "The key '%s' contained '%d' elements. All were deleted.", key, i
                )
        except Exception as e:
            log.error("Failed to delete folder '%s': %s", key, e, exc_info=True)

    @override
    def list(self, prefix: str = "") -> Iterator[str]:
        """List object keys under a logical prefix.

        Args:
            prefix: Logical prefix to inspect. Use an empty string for the
                cluster root.

        Yields:
            Logical object keys with the ``cluster_name`` prefix removed.

        """
        s3_client = self.get_s3_client()
        if not s3_client:
            log.error(
                "S3 client unavailable. Cannot list objects with prefix '%s'", prefix
            )
            return

        try:
            storage_prefix = self._storage_prefix(prefix)
            cluster_prefix = f"{self.cluster_name}/" if self.cluster_name else ""
            paginator = s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=storage_prefix)
            for page in pages:
                if "Contents" not in page:
                    continue
                for obj in page["Contents"]:
                    key = obj["Key"]
                    if cluster_prefix and key.startswith(cluster_prefix):
                        key = key[len(cluster_prefix) :]
                    yield key

        except Exception as e:
            log.error(
                "Failed to list objects with prefix '%s': %s", prefix, e, exc_info=True
            )
            return

    @override
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List object keys contained in a folder.

        Args:
            folder_path: Logical folder path to inspect.

        Yields:
            Object keys found in the folder.

        """
        yield from self.list(folder_path)

    @override
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path.

        Args:
            path: Parent path to inspect.

        Raises:
            NotImplementedError: S3 does not expose a dedicated folder listing
                operation in this implementation.

        """
        raise NotImplementedError

    @override
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restore a soft-deleted object.

        Args:
            key: Logical object key to restore.

        Raises:
            NotImplementedError: Soft delete restoration is not supported for
                S3 in this implementation.

        """
        raise NotImplementedError

    def check_authorization(self) -> None:
        """Validate AWS credentials and bucket access permissions.

        Performs a lightweight write/delete cycle against a temporary object.

        Raises:
            RuntimeError: If credentials, bucket configuration, or permissions
                are invalid.

        """
        try:
            start_time = time.time()
            if not self.s3_client:
                self.get_s3_client()

            if self.s3_client is None:
                raise RuntimeError(
                    "Authentication failed. Ensure the AWS credentials and Bucket Information are correct."
                )

            self.s3_client.put_object(
                Bucket=self.bucket_name, Key="temp_blob_for_checking", Body=b"Hi"
            )
            self.s3_client.delete_object(
                Bucket=self.bucket_name, Key="temp_blob_for_checking"
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
                    "Authentication failed. Ensure the AWS credentials and permissions are correct."
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
