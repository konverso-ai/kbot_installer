"""Bucket storage abstractions for cloud object stores."""
from abc import ABC, abstractmethod
from typing import Any, Iterator


class BucketStorage(ABC):
    """Abstract base class for cloud storage operations."""

    @abstractmethod
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve an object from the storage.

        Args:
            key: Object key to read.
            encoding: Character encoding used to decode the object content.

        Returns:
            The decoded object content, or ``None`` if the object does not exist
            or cannot be retrieved.
        """

    @abstractmethod
    def download(self, key: str, local_file_path: str):
        """Download a storageobject to a local file

        Args:
            key: Destination object key.
            local_file_path: Local path to the file to be created
        """

    @abstractmethod
    def set(self, key: str, value: Any, encoding: str = "utf-8") -> None:
        """Upload an object to the storage.

        Args:
            key: Destination object key.
            value: Object content. Strings are encoded before upload.
            encoding: Character encoding used when ``value`` is a string.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an object from the storage.

        Args:
            key: Object key to delete.
        """

    @abstractmethod
    def list(self, prefix: str = "") -> Iterator[str]:
        """List object keys under the given prefix.

        Args:
            prefix: Prefix to list objects from. Use an empty string for the
                root. Should not start with ``/`` but should end with ``/``
                when not empty.

        Yields:
            Object keys found under the prefix.
        """

    @abstractmethod
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List object keys contained in a folder.

        Args:
            folder_path: Folder path to inspect. Use an empty string for the
                root folder.

        Yields:
            Object keys found in the folder.
        """

    @abstractmethod
    def delete_folder(self, key: str) -> None:
        """Delete all objects under a folder prefix.

        Args:
            key: Folder prefix to delete.
        """

    @abstractmethod
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Restore a soft-deleted object.

        Args:
            key: Object key to restore.

        Returns:
            ``True`` if the object is available after the operation,
            ``False`` otherwise.
        """

    @abstractmethod
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path.

        Args:
            path: Parent path to inspect. Use an empty string for the root.
                Should not start with ``/`` but should end with ``/`` when not
                empty.

        Yields:
            Folder names directly inside ``path``, without their full path.
        """
