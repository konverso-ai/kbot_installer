"""Storage provider for repository operations backed by object storage."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from typing_extensions import override

from auth.base import HttpAuthBase
from git.provider.base import ProviderBase
from git.provider.config import DEFAULT_PROVIDERS_CONFIG, ProvidersConfig
from git.provider.errors import ProviderError
from storage.factory import create_bucket_storage
from utils.Logger import logger

if TYPE_CHECKING:
    from auth.base import HttpAuthBase
    from git.provider.config import ProvidersConfig
    from storage.base import StorageBase

log = logger.get_package_logger("git.provider")


class StorageProvider(ProviderBase):
    """Provider for repository operations using a configured storage backend.

    The active backend (nexus, s3, or azure) is selected from the ``storage``
    section of the providers configuration file.

    Attributes:
        branch (str): Default branch name.

    """

    name = "storage"
    base_url = ""
    branch = "master"

    def __init__(
        self,
        config: ProvidersConfig | None = None,
        auth: HttpAuthBase | None = None,
        *,
        quiet: bool = False,
    ) -> None:
        """Initialize the storage provider.

        Args:
            config: Full providers configuration. Defaults to DEFAULT_PROVIDERS_CONFIG.
            auth: HTTP authentication for the Nexus backend, when applicable.
            quiet: When True, suppress informational download output.

        """
        self._config = config or DEFAULT_PROVIDERS_CONFIG
        self._auth = auth
        self._quiet = quiet
        self._backend = self._config.storage.backend
        self.branch_used: str | None = None
        self._storage = self._create_storage()

    def _create_storage(self) -> StorageBase:
        """Create the storage backend for the configured provider backend."""
        return create_bucket_storage(
            self._backend,
            **self._config.storage.get_backend_kwargs(self._auth),
        )

    @property
    def storage(self) -> StorageBase:
        """Return the underlying object storage backend."""
        return self._storage

    @staticmethod
    def _build_object_key(repository_name: str, branch: str | None) -> str:
        """Build the object key for a repository archive."""
        branch_name = branch or "master"
        return f"{branch_name}/{repository_name}/{repository_name}_latest.tar.gz"

    def _clone_from_storage(
        self,
        repository_name: str,
        target_path: Path,
        branch_to_use: str,
    ) -> None:
        """Download and extract a repository archive from the active backend."""
        key = self._build_object_key(repository_name, branch_to_use)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        self._log(
            "Downloading repository '%s' from %s storage (key: %s)",
            repository_name,
            self._backend,
            key,
        )

        try:
            self._storage.download(key, str(target_path.parent))
        except ProviderError:
            raise
        except Exception as e:
            error_msg = (
                f"Failed to clone repository '{repository_name}' "
                f"from {self._backend} storage (key: {key}): {e}"
            )
            raise ProviderError(error_msg) from e

        self.branch_used = branch_to_use
        self._log(
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
    ) -> None:
        """Clone a repository from the configured storage backend.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, uses master.
            repository_url: Unused by the storage provider.
            repository_name: Name of the repository to clone.

        Raises:
            ProviderError: If the clone operation fails.

        """
        if repository_name is None:
            msg = "repository_name is required"
            raise ValueError(msg)
        branch_to_use = branch or self.branch
        self._clone_from_storage(repository_name, Path(target_path), branch_to_use)

    @override
    def check_remote_repository_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists on the configured storage backend."""
        key = self._build_object_key(repository_name, self.branch)
        self._log(
            "Checking if remote repository exists on %s storage: %s",
            self._backend,
            repository_name,
        )
        try:
            if "exists" in type(self._storage).__dict__:
                return bool(cast("Any", self._storage).exists(key))
            return self._storage.get(key) is not None
        except Exception:
            log.exception(
                "Error checking if repository exists on %s storage", self._backend
            )
            return False

    @override
    def get_name(self) -> str:
        """Get the name of the provider."""
        return self.name

    @override
    def get_branch(self) -> str:
        """Get the branch of the provider."""
        return self.branch_used or self.branch

    def _log(self, message: str, *args: object) -> None:
        """Log an informational message, respecting quiet mode."""
        if self._quiet:
            log.debug(message, *args)
        else:
            log.info(message, *args)
