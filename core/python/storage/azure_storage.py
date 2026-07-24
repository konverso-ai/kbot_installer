"""Azure Blob Storage implementation of bucket storage."""

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, cast

from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError
from azure.storage.blob import (
    BlobClient,
    BlobPrefix,
    BlobServiceClient,
    ContainerClient,
)
from more_itertools import chunked
from typing_extensions import override

from backend.base import BackendBase
from backend.factory import create_backend
from storage.base import StorageBase
from storage.download_utils import download_and_extract_tar_gz
from utils.Logger import logger

log = logger.get_package_logger("storage")


class AzureStorage(StorageBase):
    """``StorageBase`` backend backed by Azure Blob Storage."""

    name = "azure"
    _backend: BackendBase

    def __init__(
        self,
        container_name: str,
        account_url: str = "",
        credential_type: Literal["default_azure", "client_secret"] = "default_azure",
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        backend: BackendBase | None = None,
    ) -> None:
        """Initialize Azure storage.

        Args:
            container_name: Blob container name.
            account_url: Azure Blob Storage account URL.
            credential_type: Azure credential strategy.
            tenant_id: Azure tenant ID for client-secret auth.
            client_id: Azure client ID for client-secret auth.
            client_secret: Azure client secret for client-secret auth.
            backend: Pre-configured Azure backend. Used mainly in tests.

        """
        if backend is None:
            if not account_url:
                msg = "account_url is required when backend is not provided"
                raise ValueError(msg)
            self._backend = create_backend(
                "azure",
                account_url=account_url,
                credential_type=credential_type,
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            logged_account_url = account_url
        else:
            self._backend = backend
            logged_account_url = account_url or getattr(backend, "account_url", "")
        self.container_name = container_name
        log.debug(
            "Creating AzureStorage(account_url='%s', container_name='%s')",
            logged_account_url,
            self.container_name,
        )

    @override
    def get_name(self) -> str:
        """Return the name of the storage."""
        return self.name

    def _get_backend(self) -> BackendBase:
        """Return the backend used by this storage."""
        return self._backend

    def _get_container_client(self) -> ContainerClient | None:
        """Return the container client for the configured container."""
        blob_service_client = cast(
            "BlobServiceClient | None", self._get_backend().get_client()
        )
        if blob_service_client is None:
            return None
        return blob_service_client.get_container_client(self.container_name)

    def get_container_name(self) -> str | None:
        """Return the currently configured container name."""
        return self.container_name

    def set_container_name(self, container_name: str) -> None:
        """Switch the active container."""
        container_name = container_name.strip()
        if container_name:
            self.container_name = container_name

    @override
    def set(self, key: str, value: str | bytes, encoding: str = "utf-8") -> None:
        """Upload an object to Azure Blob Storage."""
        container_client = self._get_container_client()
        if not container_client:
            log.error("Container client unavailable. Upload aborted.")
            return
        try:
            content = value.encode(encoding) if isinstance(value, str) else value
            container_client.upload_blob(name=key, data=content, overwrite=True)
            log.debug("Object '%s' uploaded successfully to Azure Blob Storage.", key)
        except Exception:
            log.exception("Upload failed for '%s'", key)

    @override
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve and decode an object from Azure Blob Storage."""
        container_client = self._get_container_client()
        if not container_client:
            log.error(
                "Container client unavailable. Retrieval aborted. '%s'",
                self.container_name,
            )
            return None
        try:
            blob_client = container_client.get_blob_client(key)
            log.debug("CONTAINER = %s :: %s", key, self.container_name)
            # download_blob() is called without `encoding`, so it always
            # resolves to the bytes overload, not the str one.
            data = cast("bytes", blob_client.download_blob().readall())
            log.debug(
                "Successfully retrieved object from Azure Blob Storage: %s; encoding: %s",
                key,
                encoding,
            )
            return data.decode(encoding)
        except ResourceNotFoundError:
            log.exception("Path %s was not found in Bucket storage", key)
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
        container_client = self._get_container_client()
        if not container_client:
            log.exception(
                "Container client unavailable. Retrieval aborted. '%s'",
                self.container_name,
            )
            return

        blob_client = container_client.get_blob_client(key)
        with Path(local_file_path).open(mode="wb") as local_file:
            blob_data = blob_client.download_blob()
            blob_data.readinto(local_file)

    @override
    def list(self, prefix: str = "") -> Iterator[str]:
        """List blob names under the given prefix."""
        container_client = self._get_container_client()
        if not container_client:
            log.exception(
                "Container client unavailable. Cannot list objects with prefix '%s'",
                prefix,
            )
            return

        try:
            if prefix and not prefix.endswith("/"):
                prefix += "/"

            blob_list = container_client.list_blobs(name_starts_with=prefix)
            yield from [blob.name for blob in blob_list]

        except Exception:
            log.exception("Failed to list objects with prefix '%s'.", prefix)

    @override
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List blob names contained in a folder."""
        yield from self.list(folder_path)

    @override
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path."""
        container_client = self._get_container_client()
        if not container_client:
            log.exception(
                "Container client unavailable. Cannot list folders in path '%s'",
                path,
            )
            return

        try:
            if path and not path.endswith("/"):
                path += "/"

            folder_count = 0
            blob_hierarchy = container_client.walk_blobs(
                name_starts_with=path,
                delimiter="/",
            )

            for item in blob_hierarchy:
                if isinstance(item, BlobPrefix):
                    folder_name = item.prefix[len(path) :].rstrip("/")
                    if folder_name:
                        folder_count += 1
                        yield folder_name

            log.debug("Successfully listed %d folders in path '%s'", folder_count, path)

        except Exception:
            log.exception("Failed to list folders in path '%s'", path)

    @override
    def delete(self, key: str) -> None:
        """Delete a single blob from Azure Blob Storage."""
        container_client = self._get_container_client()
        if not container_client:
            log.error("Container client unavailable. Retrieval aborted.")
            return
        try:
            container_client.delete_blob(key)
            log.debug("Successfully deleted object from Azure Blob Storage: %s", key)
        except Exception:
            log.exception("Deletion failed for key='%s'", key)

    @override
    def delete_folder(self, key: str) -> None:
        """Delete all blobs under a folder prefix."""
        container_client = self._get_container_client()
        if not container_client:
            log.error("Container client unavailable. Retrieval aborted.")
            return
        blobs = chunked(container_client.list_blobs(name_starts_with=key), 20)
        i_chunk = next(blobs, None)

        if i_chunk is None:
            log.debug("This key '%s' does not exist.", key)
            return

        deleted_count = 0
        while True:
            if i_chunk is None:
                break
            blob_names = [blob.name for blob in i_chunk]
            deleted_count += len(blob_names)
            container_client.delete_blobs(*blob_names)
            i_chunk = next(blobs, None)
        log.debug(
            "The key '%s' contained '%d' elements. All were deleted.",
            key,
            deleted_count,
        )

    @override
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restore a soft-deleted blob."""
        container_client = self._get_container_client()
        if not container_client:
            log.error("Container client unavailable. Restore aborted.")
            return False

        try:
            blob_client = container_client.get_blob_client(key)
        except Exception as e:
            log.debug("Failed to get blob client for '%s': %s", key, e, exc_info=True)
            return False

        return self._undelete_blob(blob_client, key)

    def _undelete_blob(self, blob_client: BlobClient, key: str) -> bool:
        """Undelete `blob_client` if it is currently soft-deleted.

        Args:
            blob_client: Client for the blob to restore.
            key: Blob key, used for logging.

        Returns:
            ``True`` if the blob is not (or is no longer) soft-deleted.

        """
        try:
            blob_properties = blob_client.get_blob_properties()
            if not blob_properties.deleted:
                log.info("Blob '%s' is not deleted, no restoration needed.", key)
                return True
        except Exception:
            return False

        try:
            blob_client.undelete_blob()
            blob_properties = blob_client.get_blob_properties()
            log.debug("Successfully restored soft-deleted blob: %s", key)
        except ResourceNotFoundError:
            log.debug(
                "Blob '%s' not found (may have been permanently deleted or never existed).",
                key,
            )
            return False
        except Exception as e:
            log.debug(
                "Failed to restore soft-deleted blob '%s': %s",
                key,
                e,
                exc_info=True,
            )
            return False
        return not blob_properties.deleted

    def check_authorization(self) -> None:
        """Validate Azure credentials and container access permissions."""
        container_client = self._get_container_client()
        if container_client is None:
            msg = (
                "Authentication failed. Ensure the SAS token, Authorization "
                "header and Container Information are correct."
            )
            raise RuntimeError(msg)

        try:
            start_time = time.time()
            container_client.upload_blob(
                name="temp_blob_for_checking",
                data=b"Hi",
                overwrite=True,
            )
            container_client.delete_blob("temp_blob_for_checking")
            log.debug(
                "Authorization check passed. Connected to Azure Blob Storage in "
                "duration %.3f(s)",
                time.time() - start_time,
            )
        except ClientAuthenticationError as e:
            log.exception(
                "Authentication failed. Check the SAS token and Authorization header."
            )
            msg = (
                "Authentication failed. Ensure the SAS token and Authorization "
                "header are correct."
            )
            raise RuntimeError(msg) from e
        except Exception as e:
            msg_0 = "Unexpected error during authorization check"
            log.exception(msg_0)
            raise RuntimeError(msg_0) from e
