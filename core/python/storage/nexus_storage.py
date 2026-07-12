"""Nexus storage backend for repository file operations."""

import asyncio
import tempfile
from collections.abc import Coroutine, Iterator
from pathlib import Path
from typing import Any, TypeVar

from typing_extensions import override

from auth.base import HttpAuthBase
from service.nexus_service import NexusService
from storage.base import StorageBase
from utils.Logger import logger

log = logger.get_package_logger("storage")

_T = TypeVar("_T")


class NexusStorage(StorageBase):
    """Storage backend for Nexus repository operations."""

    name = "nexus"

    @override
    def get_name(self) -> str:
        """Return the name of the storage."""
        return self.name

    def __init__(
        self,
        domain: str,
        repository: str,
        auth: HttpAuthBase | None = None,
    ) -> None:
        """Initialize the Nexus storage backend.

        Args:
            domain: Domain of the Nexus instance (e.g., "example.com").
            repository: Name of the Nexus repository.
            auth: Authentication object for API requests.
                If None, operations will use public access only.

        """
        self._domain = domain
        self._repository = repository
        self._auth = auth
        self._service = NexusService(host=domain, auth=auth)

    @property
    def domain(self) -> str:
        """Domain of the Nexus instance."""
        return self._domain

    @property
    def repository(self) -> str:
        """Name of the Nexus repository."""
        return self._repository

    @staticmethod
    def _run_async(coro: Coroutine[Any, Any, _T]) -> _T:
        """Run an async coroutine from synchronous storage methods."""
        return asyncio.run(coro)

    def _repository_path(self, key: str) -> str:
        """Build the repository path for a storage key."""
        normalized_key = key.lstrip("/")
        return f"/{self._repository}/{normalized_key}"

    def _normalize_key(self, path: str | None) -> str:
        """Convert a Nexus asset path to a storage key."""
        if not path:
            return ""
        normalized = path.lstrip("/")
        repository_prefix = f"{self._repository}/"
        return normalized.removeprefix(repository_prefix)

    def _normalize_prefix(self, prefix: str) -> str:
        """Normalize a storage prefix for list operations."""
        normalized = prefix.lstrip("/")
        if normalized and not normalized.endswith("/"):
            normalized += "/"
        return normalized

    def exists(self, key: str) -> bool:
        """Return True when an object exists in the repository."""
        return self._run_async(self._service.file_exists(self._repository_path(key)))

    @override
    def get(self, key: str, encoding: str = "utf-8") -> str | None:
        """Retrieve an object from the repository."""
        if not self.exists(key):
            return None

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            self._run_async(
                self._service.get_file(self._repository_path(key), tmp_path)
            )
            return Path(tmp_path).read_text(encoding=encoding)
        except Exception:
            log.exception("Failed to retrieve object '%s' from Nexus", key)
            return None
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @override
    def download(self, key: str, local_file_path: str) -> None:
        """Download a gzipped tar archive and extract it to a directory."""
        self._run_async(
            self._service.download_and_extract(
                self._repository_path(key),
                local_file_path,
            )
        )

    @override
    def set(self, key: str, value: Any, encoding: str = "utf-8") -> None:
        """Upload is not supported for Nexus repositories."""
        msg = "Upload is not supported for Nexus storage"
        raise NotImplementedError(msg)

    @override
    def delete(self, key: str) -> None:
        """Delete is not supported for Nexus repositories."""
        msg = "Delete is not supported for Nexus storage"
        raise NotImplementedError(msg)

    @override
    def list(self, prefix: str = "") -> Iterator[str]:
        """List object keys under the given prefix."""
        nexus_files = self._run_async(self._service.list_repository(self._repository))
        normalized_prefix = self._normalize_prefix(prefix)

        for nexus_file in nexus_files:
            key = self._normalize_key(nexus_file.path)
            if not normalized_prefix or key.startswith(normalized_prefix):
                yield key

    @override
    def list_files_in_folder(self, folder_path: str = "") -> Iterator[str]:
        """List object keys contained directly in a folder."""
        normalized_folder = self._normalize_prefix(folder_path)
        for key in self.list(normalized_folder):
            relative_key = key[len(normalized_folder) :] if normalized_folder else key
            if "/" not in relative_key.rstrip("/"):
                yield key

    @override
    def delete_folder(self, key: str) -> None:
        """Delete is not supported for Nexus repositories."""
        msg = "Delete is not supported for Nexus storage"
        raise NotImplementedError(msg)

    @override
    def restore_soft_deleted_blob(self, key: str) -> bool:
        """Soft delete restoration is not supported for Nexus repositories."""
        msg = "Soft delete restoration is not supported for Nexus storage"
        raise NotImplementedError(msg)

    @override
    def list_folders(self, path: str = "") -> Iterator[str]:
        """List folders directly inside the given path."""
        normalized_path = self._normalize_prefix(path)
        seen: set[str] = set()

        for key in self.list(normalized_path):
            relative_key = key[len(normalized_path) :] if normalized_path else key
            if "/" not in relative_key:
                continue
            folder_name = relative_key.split("/", 1)[0]
            if folder_name and folder_name not in seen:
                seen.add(folder_name)
                yield folder_name
