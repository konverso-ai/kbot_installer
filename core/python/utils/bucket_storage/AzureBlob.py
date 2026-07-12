"""Azure Blob Storage implementation of bucket storage."""

import itertools
import time
from collections.abc import Iterator
from typing import Any
from typing_extensions import override

from azure.core.exceptions import (
    ClientAuthenticationError,
    ResourceExistsError,
    ResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobPrefix, BlobServiceClient, ContainerClient

from utils.bucket_storage.base import BucketStorage
from utils.Logger import logger

log = logger.get_package_logger("bucket_storage")


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


class AzureBlob(BucketStorage):
    """``BucketStorage`` backend backed by Azure Blob Storage."""

    # No name, such that this class will not be loaded in factory
    name = ""

    def __init__(
        self, account_url: str | None = None, container_name: str | None = None
    ) -> None:
        """Initialize Azure settings from arguments or bot configuration.

        Args:
            account_url: Azure storage account URL. Falls back to
                ``kbot_storage_account`` from configuration.
            container_name: Blob container name. Falls back to
                ``storage_account_container_name`` from configuration.

        """
        self.account_url = account_url
        self.container_name = container_name
        from Bot import Bot  # pylint: disable=import-error

        config = Bot()
        if self.account_url is None:
            self.account_url = config.GetConfig("kbot_storage_account")
        if self.container_name is None:
            self.container_name = config.GetConfig("storage_account_container_name")
        if not self.container_name:
            log.debug(
                "Missing storage account name for AzureBlob storage. Cannot be used. We recommend adding 'storage_account_container_name = %s",
                self.container_name,
            )
        self.container_client = None
        log.debug(
            "Creating AzureBlob(account_url='%s', container_name='%s')",
            self.account_url,
            self.container_name,
        )

    def __connect_to_blob_service(self) -> BlobServiceClient | None:
        """Create and cache an Azure Blob service client.

        Returns:
            A connected ``BlobServiceClient``, or ``None`` if the account URL
            is missing or the connection fails.

        """
        if not self.account_url:
            log.warning(
                "Azure Blob storage for account url '%s' is configured.",
                self.account_url,
            )
            return None
        if not self.container_name:
            log.warning("Azure Blob storage container name is not configured.")
            return None
        try:
            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(
                self.account_url, credential=credential
            )
            self.container_client = blob_service_client.get_container_client(
                self.container_name
            )
            log.info(
                "Successfully connected to Azure Blob storage for account name: %s",
                self.account_url,
            )
            return blob_service_client
        except ResourceNotFoundError:
            log.warning(
                "Azure Blob storage for account url '%s' does not exist.",
                self.account_url,
            )
            return None
        except Exception as e:
            log.error(
                "Failed to connect to Azure Storage account. Error: %s",
                e,
                exc_info=True,
            )
            return None

    def create_container(self, blob_service_client: BlobServiceClient) -> None:
        """Create the configured container when it does not already exist.

        Args:
            blob_service_client: Connected Azure blob service client.

        """
        if not self.container_name:
            log.warning("Cannot create Azure Blob container without a container name.")
            return
        try:
            blob_service_client.create_container(name=self.container_name)
        except ResourceExistsError:
            log.fine("Azure Blob Container %s already exists", self.container_name)
        except Exception as e:
            log.error(
                "Couldn't create Azure Blob Container %s due to %s",
                self.container_name,
                str(e),
            )

    def get_container_name(self) -> str | None:
        """Return the currently configured container name.

        Returns:
            The active blob container name.

        """
        return self.container_name

    def set_container_name(self, container_name: str) -> None:
        """Switch the active container after validating connectivity.

        Args:
            container_name: New container name to use.

        """
        container_name = container_name.strip()
        if not container_name:
            log.warning("Cannot update the container with nothing input information.")
            return
        container_client = self._get_container_client(container_name=container_name)
        if container_client is None:
            log.warning(
                "Cannot update container information. Please review container name: %s",
                container_name,
            )
            return
        log.info("Update container client and related information.")
        self.container_name = container_name
        self.container_client = container_client

    def _get_container_client(self, container_name: str) -> ContainerClient | None:
        """Return a container client for a specific container.

        Args:
            container_name: Container name to connect to.

        Returns:
            A connected container client, or ``None`` if initialization fails.

        """
        service_client = self.__connect_to_blob_service()
        if service_client:
            try:
                self.container_client = service_client.get_container_client(
                    container_name
                )
                log.info(
                    "Connected to Azure Blob Storage container '%s'.", container_name
                )
                return self.container_client
            except ResourceNotFoundError:
                log.warning("Container '%s' does not exist.", container_name)
                return None
            except Exception as e:
                log.error(
                    "Failed to connect to Container on Azure Blob. Error: %s",
                    e,
                    exc_info=True,
                )
                return None
        log.error("Container client initialization failed.")
        return None

    def get_container_client(self) -> ContainerClient | None:
        """Return the cached container client, initializing it when needed.

        Returns:
            A connected container client, or ``None`` if initialization fails.

        """
        if self.container_client:
            return self.container_client
        if not self.container_name:
            return None
        return self._get_container_client(container_name=self.container_name)

    @override
    def set(
        self,
        key: str,
        value: str | bytes | Any,
        encoding: str = "utf-8",
        raise_on_status=False,
    ) -> None:
        """Upload an object to Azure Blob Storage.

        Args:
            key: Blob name.
            value: Object content. Strings are encoded before upload.
            encoding: Character encoding used when ``value`` is a string.

        """
        container_client = self.get_container_client()
        if not container_client:
            log.error("Container client unavailable. Upload aborted.")
            return
        try:
            content = value.encode(encoding) if isinstance(value, str) else value
            container_client.upload_blob(name=key, data=content, overwrite=True)
            log.debug("Object '%s' uploaded successfully to Azure Blob Storage.", key)
        except Exception as e:
            log.error("Upload failed for '%s': %s", key, e, exc_info=True)
            if raise_on_status:
                raise

    @override
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve and decode an object from Azure Blob Storage.

        Args:
            key: Blob name.
            encoding: Character encoding used to decode the object content.

        Returns:
            The decoded object content, or ``None`` if retrieval fails.

        """
        container_client = self.get_container_client()
        if not container_client:
            log.error(
                "Container client unavailable. Retrieval aborted. '%s'",
                self.container_name,
            )
            return None
        try:
            blob_client = container_client.get_blob_client(key)
            log.debug("CONTAINER = %s :: %s", key, self.container_name)
            data = blob_client.download_blob().readall()
            log.debug(
                "Successfully retrieved object from Azure Blob Storage: %s; encoding: %s",
                key,
                encoding,
            )
            if isinstance(data, bytes):
                return data.decode(encoding)
            return data
        except ResourceNotFoundError:
            log.error("Path %s was not found in Bucket storage", key)
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
        container_client = self.get_container_client()
        if not container_client:
            log.error(
                "Container client unavailable. Retrieval aborted. '%s'",
                self.container_name,
            )
            return

        blob_client = container_client.get_blob_client(key)
        with open(local_file_path, "wb") as local_file:
            blob_data = blob_client.download_blob()
            blob_data.readinto(local_file)

    @override
    def list(self, prefix: str = "") -> Iterator[str]:
        """List blob names under the given prefix.

        Args:
            prefix: Prefix to inspect. Use an empty string for the container
                root. A trailing slash is appended automatically when needed.

        Yields:
            Blob names found under the prefix.

        """
        container_client = self.get_container_client()
        if not container_client:
            log.error(
                "Container client unavailable. Cannot list objects with prefix '%s'",
                prefix,
            )
            return

        try:
            if prefix and not prefix.endswith("/"):
                prefix += "/"

            blob_list = container_client.list_blobs(name_starts_with=prefix)
            yield from [blob.name for blob in blob_list]

        except Exception as e:
            log.error("Failed to list objects with prefix '%s': %s", prefix, str(e))
            return

    @override
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List blob names contained in a folder.

        Args:
            folder_path: Folder path to inspect. Use an empty string for the
                root folder.

        Yields:
            Blob names found in the folder.

        """
        yield from self.list(folder_path)

    @override
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path.

        Args:
            path: Parent path to inspect. Use an empty string for the root.
                A trailing slash is appended automatically when needed.

        Yields:
            Folder names directly inside ``path``, without their full path.

        """
        container_client = self.get_container_client()
        if not container_client:
            log.error(
                "Container client unavailable. Cannot list folders in path '%s'", path
            )
            return

        # Cursor comment to review and potentially adress:
        # list_folders treats every walk_blobs item with a name as a folder, but blob objects at the current level also have name,
        # so file names can be returned as folders alongside real prefixes.
        #
        try:
            if path and not path.endswith("/"):
                path += "/"

            folder_count = 0
            blob_hierarchy = container_client.walk_blobs(
                name_starts_with=path, delimiter="/"
            )

            for item in blob_hierarchy:
                if isinstance(item, BlobPrefix):
                    folder_name = item.prefix[len(path) :].rstrip("/")
                    if folder_name:
                        folder_count += 1
                        yield folder_name

            log.debug("Successfully listed %d folders in path '%s'", folder_count, path)

        except Exception as e:
            log.error("Failed to list folders in path '%s': %s", path, str(e))
            return

    @override
    def delete(self, key: str) -> None:
        """Delete a single blob from Azure Blob Storage.

        Args:
            key: Blob name to delete.

        """
        container_client = self.get_container_client()
        if not container_client:
            log.error("Container client unavailable. Retrieval aborted.")
            return
        try:
            container_client.delete_blob(key)
            log.debug("Successfully deleted object from Azure Blob Storage: %s", key)
        except Exception:
            log.exception("Deletion failed for key='%s'")
        return

    @override
    def delete_folder(self, key: str) -> None:
        """Delete all blobs under a folder prefix.

        Args:
            key: Folder prefix to delete.

        """
        container_client = self.get_container_client()
        if not container_client:
            log.error("Container client unavailable. Retrieval aborted.")
            return
        blobs = chunks(container_client.list_blobs(name_starts_with=key), 20)
        i_chunk = next(blobs, None)

        if i_chunk is None:
            log.debug("This key '%s' does not exist.", key)
            return

        i = 0
        while True:
            if i_chunk is None:
                break
            blob_names = [blob.name for blob in i_chunk]
            i += len(blob_names)
            container_client.delete_blobs(*blob_names)
            i_chunk = next(blobs, None)
        log.debug("The key '%s' contained '%d' elements. All were deleted.", key, i)

    @override
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restore a soft-deleted blob.

        Args:
            key: Blob name to restore.

        Returns:
            ``True`` if the blob is available after the operation, ``False``
            otherwise.

        """
        container_client = self.get_container_client()
        if not container_client:
            log.error("Container client unavailable. Restore aborted.")
            return False

        try:
            blob_client = container_client.get_blob_client(key)
        except Exception as e:
            log.debug("Failed to get blob client for '%s': %s", key, e, exc_info=True)
            return False

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
            return not blob_properties.deleted
        except ResourceNotFoundError:
            log.debug(
                "Blob '%s' not found (may have been permanently deleted or never existed).",
                key,
            )
            return False
        except Exception as e:
            log.debug(
                "Failed to restore soft-deleted blob '%s': %s", key, e, exc_info=True
            )
            return False

    def check_authorization(self) -> None:
        """Validate Azure credentials and container access permissions.

        Performs a lightweight write/delete cycle against a temporary blob.

        Raises:
            RuntimeError: If credentials, container configuration, or
                permissions are invalid.

        """
        try:
            start_time = time.time()
            if not self.container_client:
                self.get_container_client()

            if self.container_client is None:
                raise RuntimeError(
                    "Authentication failed. Ensure the SAS token, Authorization header and Container Information are correct."
                )

            self.container_client.upload_blob(
                name="temp_blob_for_checking", data=b"Hi", overwrite=True
            )
            self.container_client.delete_blob("temp_blob_for_checking")
            log.debug(
                "Authorization check passed. Connected to Azure Blob Storage in duration %.3f(s)",
                time.time() - start_time,
            )
        except ClientAuthenticationError as e:
            log.error(
                "Authentication failed. Check the SAS token and Authorization header. Error: %s",
                e,
                exc_info=True,
            )
            raise RuntimeError(
                "Authentication failed. Ensure the SAS token and Authorization header are correct."
            ) from e
        except Exception as e:
            log.error(
                "Unexpected error during authorization check. Error: %s",
                e,
                exc_info=True,
            )
            raise RuntimeError("Unexpected error during authorization check") from e
