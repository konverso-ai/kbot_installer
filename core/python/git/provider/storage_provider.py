"""Storage provider for repository operations backed by object storage."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from typing_extensions import override

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.utils import build_object_key
from utils.Logger import logger

if TYPE_CHECKING:
    from storage.base import StorageBase

log = logger.get_package_logger("git.provider")


class StorageProvider(ProviderBase):
    """Provider for repository operations using an object storage backend.

    Attributes:
        branch (str): Default branch name.

    """

    name = "storage"
    base_url = ""
    branch = "master"

    def __init__(self, storage: StorageBase) -> None:
        """Initialize the storage provider.

        Args:
            storage: Storage backend to use for repository operations.

        """
        self._storage = storage
        self.branch_used: str | None = None

    def _clone_from_storage(
        self,
        repository_name: str,
        target_path: Path,
        branch_to_use: str,
        commit: str | None = None,
    ) -> None:
        """Download and extract a repository archive from the active backend."""
        key = build_object_key(repository_name, branch_to_use, commit)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        log.info(
            "Downloading repository '%s' from storage (key: %s)",
            repository_name,
            key,
        )

        try:
            self._storage.download(key, str(target_path.parent))
        except ProviderError:
            raise
        except Exception as e:
            error_msg = f"Failed to clone repository '{repository_name}' from storage (key: {key}): {e}"
            raise ProviderError(error_msg) from e

        self.branch_used = branch_to_use
        log.info(
            "Successfully cloned repository '%s' to %s",
            repository_name,
            target_path,
        )

    @override
    def clone_and_checkout(
        self,
        target_path: str | Path,
        branch: str | None = None,
        *,
        _repository_url: str | None = None,
        repository_name: str | None = None,
        commit: str | None = None,
    ) -> None:
        """Clone a repository from the configured storage backend.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, uses master.
            repository_url: Unused by the storage provider.
            repository_name: Name of the repository to clone.
            commit: Specific commit to pin the archive to. If None, the "latest"
                archive for the branch is downloaded instead.

        Raises:
            ProviderError: If the clone operation fails.

        """
        if repository_name is None:
            msg = "repository_name is required"
            raise ValueError(msg)
        branch_to_use = branch or self.branch
        self._clone_from_storage(repository_name, Path(target_path), branch_to_use, commit)

    @override
    def check_remote_repository_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists on the configured storage backend."""
        key = build_object_key(repository_name, self.branch)
        log.info("Checking if remote repository exists on storage: %s", repository_name)
        try:
            if "exists" in type(self._storage).__dict__:
                return bool(cast("Any", self._storage).exists(key))
            return self._storage.get(key) is not None
        except Exception:
            log.exception("Error checking if repository exists on storage")
            return False

    @override
    def get_name(self) -> str:
        """Get the name of the provider."""
        return self.name

    @override
    def get_branch(self) -> str:
        """Get the branch of the provider."""
        return self.branch_used or self.branch
