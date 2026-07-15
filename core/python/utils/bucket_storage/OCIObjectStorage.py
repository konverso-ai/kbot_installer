"""OCI Object Storage implementation of bucket storage."""
import itertools
import time
from collections.abc import Iterator
from typing import Any

import oci
from oci.exceptions import ServiceError
from oci.object_storage.models import BatchDeleteObjectIdentifier, BatchDeleteObjectsDetails

from utils import logger
from utils.bucket_storage import BucketStorage

log = logger.getPackageLogger('bucket_storage')


def chunks(iterable, n: int) -> Iterator[list]:
    """Split an iterable into fixed-size chunks."""
    iterator = iter(iterable)
    while True:
        chunk = list(itertools.islice(iterator, n))
        if not chunk:
            break
        yield chunk


class OCIObjectStorage(BucketStorage):
    """``BucketStorage`` backend backed by OCI Object Storage."""

    # No name, such that this class will not be loaded in factory
    name = ""

    def __init__(
        self,
        auth_method: str,
        bucket_name: str | None,
        namespace: str | None = None,
        cluster_name: str | None = None,
    ) -> None:
        """Initialize OCI Object Storage settings."""
        self.auth_method = auth_method or "instance_principal"
        self.bucket_name = bucket_name
        self.namespace = namespace
        self.cluster_name = cluster_name
        self.object_storage_client = None
        log.debug(
            "Creating OCIObjectStorage(auth_method='%s', bucket_name='%s', namespace='%s')",
            self.auth_method,
            self.bucket_name,
            self.namespace,
        )

    def __connect_to_object_storage_service(self):
        """Create and cache an OCI Object Storage client using instance identity."""
        if not self.bucket_name:
            log.warning("OCI Object Storage bucket name is not configured.")
            return None

        try:
            if self.auth_method == "resource_principal":
                signer = oci.auth.signers.get_resource_principals_signer()
            elif self.auth_method == "instance_principal":
                signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            else:
                log.error(
                    "Unsupported auth_method '%s'. Expected 'instance_principal' or 'resource_principal'.",
                    self.auth_method,
                )
                return None

            client = oci.object_storage.ObjectStorageClient(
                config={
                    "region": "eu-paris-1",
                },
                signer=signer,
            )
            log.info(
                "Successfully connected to OCI Object Storage for bucket: %s",
                self.bucket_name,
            )
            return client
        except Exception as e:
            log.error("Failed to connect to OCI Object Storage. Error: %s", e, exc_info=True)
            self.object_storage_client = None
            return None

    def __resolve_namespace(self, client) -> str | None:
        if self.namespace:
            return self.namespace

        try:
            self.namespace = client.get_namespace().data
            return self.namespace
        except Exception as e:
            log.error("Failed to resolve OCI Object Storage namespace. Error: %s", e, exc_info=True)
            return None

    def get_bucket_name(self) -> str | None:
        """Return the currently configured bucket name."""
        return self.bucket_name

    def set_bucket_name(self, bucket_name: str) -> None:
        """Switch the active bucket after validating connectivity."""
        bucket_name = bucket_name.strip()
        if not bucket_name:
            log.warning("Cannot update the bucket with empty information.")
            return

        previous_bucket = self.bucket_name
        self.bucket_name = bucket_name
        client = self._get_object_storage_client(bucket_name=bucket_name)
        if client is None:
            self.bucket_name = previous_bucket
            self.object_storage_client = None
            log.warning(
                "Cannot update bucket information. Please review bucket name: %s",
                bucket_name,
            )
            return

        log.info("Update OCI Object Storage client and related information.")
        self.object_storage_client = client

    def _get_object_storage_client(self, bucket_name: str | None = None):
        """Return an Object Storage client connected to a specific bucket."""
        bucket_name = bucket_name or self.bucket_name
        client = self.__connect_to_object_storage_service()
        if not client:
            self.object_storage_client = None
            log.error("OCI Object Storage client initialization failed.")
            return None

        namespace = self.__resolve_namespace(client)
        if not namespace:
            self.object_storage_client = None
            return None

        try:
            # Validate access via list_objects rather than get_bucket: IAM policies scoped to
            # "manage objects" (not "manage/inspect buckets") make get_bucket return a 404
            # even though the bucket exists and is otherwise fully accessible.
            client.list_objects(namespace, bucket_name, limit=1)
            self.object_storage_client = client
            log.info("Connected to OCI Object Storage bucket '%s'.", bucket_name)
            return self.object_storage_client
        except ServiceError as e:
            self.object_storage_client = None
            if e.status == 404:
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
            self.object_storage_client = None
            log.error("Failed to connect to OCI bucket. Error: %s", e, exc_info=True)
            return None

    def get_object_storage_client(self):
        """Return the cached Object Storage client, initializing it when needed."""
        if self.object_storage_client:
            return self.object_storage_client
        return self._get_object_storage_client(bucket_name=self.bucket_name)

    def _prefixed_key(self, key: str) -> str:
        if self.cluster_name:
            return f"{self.cluster_name}/{key}"
        return key

    def _storage_prefix(self, prefix: str = "") -> str:
        if self.cluster_name:
            storage_prefix = f"{self.cluster_name}/{prefix}" if prefix else f"{self.cluster_name}/"
        else:
            storage_prefix = prefix
        if storage_prefix and not storage_prefix.endswith('/'):
            storage_prefix += '/'
        return storage_prefix

    def _logical_key(self, storage_key: str) -> str:
        cluster_prefix = f"{self.cluster_name}/" if self.cluster_name else ""
        if cluster_prefix and storage_key.startswith(cluster_prefix):
            return storage_key[len(cluster_prefix):]
        return storage_key

    def _iter_object_names(self, prefix: str = "") -> Iterator[str]:
        client = self.get_object_storage_client()
        if not client:
            return

        namespace = self.__resolve_namespace(client)
        if not namespace:
            return

        storage_prefix = self._storage_prefix(prefix)
        start = None

        while True:
            response = client.list_objects(
                namespace,
                self.bucket_name,
                prefix=storage_prefix or None,
                start=start,
            )
            for obj in response.data.objects or []:
                yield obj.name

            start = response.data.next_start_with
            if not start:
                break

    def set(self, key: str, value: str | bytes | Any, encoding: str = "utf-8", raise_on_status=False) -> None:
        """Upload an object to OCI Object Storage."""
        key = self._prefixed_key(key)

        client = self.get_object_storage_client()
        if not client:
            log.error("OCI Object Storage client unavailable. Upload aborted.")
            if raise_on_status:
                raise RuntimeError("OCI Object Storage client unavailable.")
            return

        namespace = self.__resolve_namespace(client)
        if not namespace:
            if raise_on_status:
                raise RuntimeError("OCI Object Storage namespace could not be resolved.")
            return

        try:
            content = value.encode(encoding) if isinstance(value, str) else value
            client.put_object(namespace, self.bucket_name, key, content)
            log.debug("Object '%s' uploaded successfully to OCI Object Storage.", key)
        except Exception as e:
            log.error("Upload failed for '%s': %s", key, e, exc_info=True)
            if raise_on_status:
                raise

    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve and decode an object from OCI Object Storage."""
        key = self._prefixed_key(key)

        client = self.get_object_storage_client()
        if not client:
            log.error(
                "OCI Object Storage client unavailable. Retrieval aborted. '%s'",
                self.bucket_name,
            )
            return None

        namespace = self.__resolve_namespace(client)
        if not namespace:
            return None

        try:
            response = client.get_object(namespace, self.bucket_name, key)
            content = response.data.content
            data = content.read() if hasattr(content, "read") else content
            log.debug(
                "Successfully retrieved object from OCI Object Storage: %s; encoding: %s",
                key,
                encoding,
            )
            return data.decode(encoding)
        except ServiceError as e:
            if e.status == 404:
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

    def download(self, key: str, local_file_path: str):
        """Download a storage object to a local file."""
        key = self._prefixed_key(key)

        client = self.get_object_storage_client()
        if not client:
            log.error(
                "OCI Object Storage client unavailable. Retrieval aborted. '%s'",
                self.bucket_name,
            )
            return None

        namespace = self.__resolve_namespace(client)
        if not namespace:
            return None

        try:
            response = client.get_object(namespace, self.bucket_name, key)
            content = response.data.content
            with open(local_file_path, "wb") as local_file:
                local_file.write(content.read() if hasattr(content, "read") else content)
        except Exception as e:
            log.error("Download failed for key='%s': %s", key, e, exc_info=True)
            return None

    def delete(self, key: str) -> None:
        """Delete a single object from OCI Object Storage."""
        key = self._prefixed_key(key)

        client = self.get_object_storage_client()
        if not client:
            log.error("OCI Object Storage client unavailable. Deletion aborted.")
            return None

        namespace = self.__resolve_namespace(client)
        if not namespace:
            return None

        try:
            client.delete_object(namespace, self.bucket_name, key)
            log.debug("Successfully deleted object from OCI Object Storage: %s", key)
        except Exception as e:
            log.exception("Deletion failed for key='%s': %s", key, e)
        return None

    def delete_folder(self, key: str) -> None:
        """Delete all objects under a folder prefix."""
        client = self.get_object_storage_client()
        if not client:
            log.error("OCI Object Storage client unavailable. Deletion aborted.")
            return

        namespace = self.__resolve_namespace(client)
        if not namespace:
            return

        try:
            object_names = list(self._iter_object_names(key))
            if not object_names:
                log.debug("This key '%s' does not exist.", key)
                return

            for chunk in chunks(object_names, 1000):
                batch_delete_details = BatchDeleteObjectsDetails(
                    objects=[
                        BatchDeleteObjectIdentifier(object_name=object_name)
                        for object_name in chunk
                    ]
                )
                client.batch_delete_objects(
                    namespace,
                    self.bucket_name,
                    batch_delete_details,
                )

            log.debug(
                "The key '%s' contained '%d' elements. All were deleted.",
                key,
                len(object_names),
            )
        except Exception as e:
            log.error("Failed to delete folder '%s': %s", key, e, exc_info=True)

    def list(self, prefix: str = "") -> Iterator[str]:
        """List object keys under a logical prefix."""
        client = self.get_object_storage_client()
        if not client:
            log.error(
                "OCI Object Storage client unavailable. Cannot list objects with prefix '%s'",
                prefix,
            )
            return []

        try:
            for storage_key in self._iter_object_names(prefix):
                yield self._logical_key(storage_key)
        except Exception as e:
            log.error("Failed to list objects with prefix '%s': %s", prefix, e, exc_info=True)
            return []

    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List object keys contained in a folder."""
        yield from self.list(folder_path)

    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path."""
        client = self.get_object_storage_client()
        if not client:
            log.error(
                "OCI Object Storage client unavailable. Cannot list folders in path '%s'",
                path,
            )
            return []

        namespace = self.__resolve_namespace(client)
        if not namespace:
            return []

        storage_prefix = self._storage_prefix(path)
        cluster_prefix = f"{self.cluster_name}/" if self.cluster_name else ""
        start = None

        try:
            while True:
                response = client.list_objects(
                    namespace,
                    self.bucket_name,
                    prefix=storage_prefix or None,
                    delimiter='/',
                    start=start,
                )
                for folder_prefix in response.data.prefixes or []:
                    folder_name = folder_prefix
                    if cluster_prefix and folder_name.startswith(cluster_prefix):
                        folder_name = folder_name[len(cluster_prefix):]
                    folder_name = folder_name.rstrip('/')
                    if folder_name:
                        yield folder_name.split('/')[-1]

                start = response.data.next_start_with
                if not start:
                    break
        except Exception as e:
            log.error("Failed to list folders in path '%s': %s", path, e, exc_info=True)
            return []

    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restore a soft-deleted object."""
        raise NotImplementedError

    def check_authorization(self) -> None:
        """Validate OCI identity and bucket access permissions."""
        try:
            start_time = time.time()
            client = self.get_object_storage_client()
            if client is None:
                raise RuntimeError(
                    "Authentication failed. Ensure the OCI bucket information is correct."
                )

            namespace = self.__resolve_namespace(client)
            if not namespace:
                raise RuntimeError(
                    "Authentication failed. Could not resolve the OCI Object Storage namespace."
                )

            temp_key = self._prefixed_key("temp_blob_for_checking")
            client.put_object(namespace, self.bucket_name, temp_key, b"Hi")
            client.delete_object(namespace, self.bucket_name, temp_key)
            log.debug(
                "Authorization check passed. Connected to OCI Object Storage in duration %.3f(s)",
                time.time() - start_time,
            )
        except ServiceError as e:
            if e.status in {401, 403, 404}:
                log.error(
                    "Authentication failed. Check the OCI permissions and bucket. Error: %s",
                    e,
                    exc_info=True,
                )
                raise RuntimeError(
                    "Authentication failed. Ensure the OCI permissions and bucket are correct."
                ) from e
            log.error("Unexpected error during authorization check. Error: %s", e, exc_info=True)
            raise RuntimeError("Unexpected error during authorization check") from e
        except Exception as e:
            log.error("Unexpected error during authorization check. Error: %s", e, exc_info=True)
            raise RuntimeError("Unexpected error during authorization check") from e
