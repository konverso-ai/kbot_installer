"""Oracle Cloud Infrastructure (OCI) Object Storage implementation of bucket storage."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

from oci.exceptions import ServiceError
from typing_extensions import override

from backend.factory import create_backend
from storage.base import StorageBase
from storage.download_utils import download_and_extract_tar_gz
from utils.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Iterator

    from oci.object_storage import ObjectStorageClient

    from backend.oci_backend import OciBackend

log = logger.get_package_logger("storage")


class OciStorage(StorageBase):
    """``StorageBase`` backend backed by Oracle Cloud Infrastructure Object Storage."""

    name = "oci"
    _backend: OciBackend

    @override
    def get_name(self) -> str:
        """Return the name of the storage."""
        return self.name

    def __init__(
        self,
        bucket_name: str,
        namespace_name: str,
        region: str = "eu-frankfurt-1",
        user_ocid: str | None = None,
        tenancy_ocid: str | None = None,
        fingerprint: str | None = None,
        private_key_path: str | None = None,
        pass_phrase: str | None = None,
        backend: OciBackend | None = None,
    ) -> None:
        """Initialize OCI Object Storage.

        Args:
            bucket_name: OCI Object Storage bucket name.
            namespace_name: Object Storage namespace of the tenancy.
            region: OCI region identifier.
            user_ocid: OCID of the calling user.
            tenancy_ocid: OCID of the tenancy containing the user.
            fingerprint: Fingerprint of the public key uploaded for the user.
            private_key_path: Path to the PEM-encoded API signing key file.
            pass_phrase: Passphrase protecting the private key, if any.
            backend: Pre-configured OCI backend. Used mainly in tests.

        """
        self._backend = backend or cast(
            "OciBackend",
            create_backend(
                "oci",
                region=region,
                user_ocid=user_ocid,
                tenancy_ocid=tenancy_ocid,
                fingerprint=fingerprint,
                private_key_path=private_key_path,
                pass_phrase=pass_phrase,
            ),
        )
        self.bucket_name = bucket_name
        self.namespace_name = namespace_name
        log.debug(
            "Creating OciStorage(bucket_name='%s', namespace_name='%s')",
            self.bucket_name,
            self.namespace_name,
        )

    def _get_backend(self) -> OciBackend:
        """Return the backend used by this storage."""
        return self._backend

    def _get_client(self) -> ObjectStorageClient | None:
        """Return the OCI Object Storage client from the configured backend."""
        return cast("ObjectStorageClient | None", self._get_backend().get_client())

    def get_bucket_name(self) -> str | None:
        """Return the currently configured bucket name."""
        return self.bucket_name

    def set_bucket_name(self, bucket_name: str) -> None:
        """Switch the active bucket."""
        bucket_name = bucket_name.strip()
        if bucket_name:
            self.bucket_name = bucket_name

    @override
    def set(self, key: str, value: str | bytes, encoding: str = "utf-8") -> None:
        """Upload an object to OCI Object Storage."""
        client = self._get_client()
        if not client:
            log.error("OCI client unavailable. Upload aborted.")
            return
        try:
            content = value.encode(encoding) if isinstance(value, str) else value
            client.put_object(self.namespace_name, self.bucket_name, key, content)
            log.debug("Object '%s' uploaded successfully to OCI Object Storage.", key)
        except Exception:
            log.exception("Upload failed for '%s'", key)

    @override
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve and decode an object from OCI Object Storage."""
        client = self._get_client()
        if not client:
            log.error(
                "OCI client unavailable. Retrieval aborted. '%s'",
                self.bucket_name,
            )
            return None
        try:
            response = client.get_object(self.namespace_name, self.bucket_name, key)
            data = response.data.content
            log.debug(
                "Successfully retrieved object from OCI Object Storage: %s; encoding: %s",
                key,
                encoding,
            )
            return data.decode(encoding)
        except ServiceError as e:
            if e.status == 404:  # noqa: PLR2004
                log.exception("Path %s was not found in Bucket storage", key)
            else:
                log.exception(
                    "Retrieval failed for key='%s'; encoding=%s",
                    key,
                    encoding,
                )
        except Exception:
            log.exception(
                "Retrieval failed for key='%s'; encoding=%s",
                key,
                encoding,
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
        client = self._get_client()
        if not client:
            log.error(
                "OCI client unavailable. Retrieval aborted. '%s'",
                self.bucket_name,
            )
            return

        response = client.get_object(self.namespace_name, self.bucket_name, key)
        with Path(local_file_path).open(mode="wb") as local_file:
            local_file.writelines(
                response.data.raw.stream(1024 * 1024, decode_content=False)
            )

    @override
    def delete(self, key: str) -> None:
        """Delete a single object from OCI Object Storage."""
        client = self._get_client()
        if not client:
            log.error("OCI client unavailable. Deletion aborted.")
            return
        try:
            client.delete_object(self.namespace_name, self.bucket_name, key)
            log.debug("Successfully deleted object from OCI Object Storage: %s", key)
        except Exception:
            log.exception("Deletion failed for key='%s'", key)

    @override
    def delete_folder(self, key: str) -> None:
        """Delete all objects under a folder prefix."""
        client = self._get_client()
        if not client:
            log.error("OCI client unavailable. Deletion aborted.")
            return

        try:
            prefix = key if not key or key.endswith("/") else f"{key}/"
            deleted_count = 0
            for object_name in self.list(prefix):
                client.delete_object(self.namespace_name, self.bucket_name, object_name)
                deleted_count += 1

            if deleted_count == 0:
                log.debug("This key '%s' does not exist.", key)
            else:
                log.debug(
                    "The key '%s' contained '%d' elements. All were deleted.",
                    key,
                    deleted_count,
                )
        except Exception:
            log.exception("Failed to delete folder '%s'", key)

    @override
    def list(self, prefix: str = "") -> Iterator[str]:
        """List object keys under a logical prefix."""
        client = self._get_client()
        if not client:
            log.exception(
                "OCI client unavailable. Cannot list objects with prefix '%s'",
                prefix,
            )
            return

        try:
            start = None
            while True:
                response = client.list_objects(
                    self.namespace_name,
                    self.bucket_name,
                    prefix=prefix,
                    start=start,
                    fields="name",
                )
                for object_summary in response.data.objects:
                    yield object_summary.name
                start = response.data.next_start_with
                if not start:
                    break
        except Exception:
            log.exception(
                "Failed to list objects with prefix '%s'",
                prefix,
            )

    @override
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List object keys contained in a folder."""
        yield from self.list(folder_path)

    @override
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path."""
        client = self._get_client()
        if not client:
            log.exception(
                "OCI client unavailable. Cannot list folders in path '%s'",
                path,
            )
            return

        try:
            response = client.list_objects(
                self.namespace_name,
                self.bucket_name,
                prefix=path,
                delimiter="/",
                fields="name",
            )
            for object_prefix in response.data.prefixes or []:
                folder_name = object_prefix[len(path) :].rstrip("/")
                if folder_name:
                    yield folder_name
        except Exception:
            log.exception("Failed to list folders in path '%s'", path)

    @override
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restore a soft-deleted object."""
        raise NotImplementedError

    def check_authorization(self) -> None:
        """Validate OCI credentials and bucket access permissions."""
        client = self._get_client()
        if client is None:
            msg = (
                "Authentication failed. Ensure the OCI credentials and "
                "Bucket Information are correct."
            )
            raise RuntimeError(msg)

        try:
            start_time = time.time()
            client.put_object(
                self.namespace_name,
                self.bucket_name,
                "temp_blob_for_checking",
                b"Hi",
            )
            client.delete_object(
                self.namespace_name,
                self.bucket_name,
                "temp_blob_for_checking",
            )
            log.debug(
                "Authorization check passed. Connected to OCI Object Storage in "
                "duration %.3f(s)",
                time.time() - start_time,
            )
        except ServiceError as e:
            if e.status in {401, 403}:
                log.exception(
                    "Authentication failed. Check the OCI credentials and permissions.",
                )
                msg_0 = (
                    "Authentication failed. Ensure the OCI credentials and "
                    "permissions are correct."
                )
                raise RuntimeError(msg_0) from e
            log.exception("Unexpected error during authorization check.")
            msg_1 = "Unexpected error during authorization check"
            raise RuntimeError(msg_1) from e
        except Exception as e:
            log.exception("Unexpected error during authorization check.")
            msg_2 = "Unexpected error during authorization check"
            raise RuntimeError(msg_2) from e
