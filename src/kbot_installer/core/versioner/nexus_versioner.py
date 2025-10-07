"""Nexus versioner for repository operations.

This module implements the NexusVersioner class that handles repository
operations using the Nexus API for downloading repositories as tar.gz archives.
"""

import logging
from pathlib import Path

import httpx

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase
from kbot_installer.core.provider.utils import FileInfo
from kbot_installer.core.utils import optimized_download_and_extract
from kbot_installer.core.versioner.versioner_base import VersionerBase, VersionerError

logger = logging.getLogger(__name__)

# HTTP status codes
HTTP_OK = 200


class NexusVersioner(VersionerBase):
    """Versioner for Nexus repository operations.

    This versioner handles operations on Nexus repositories using the Nexus API.
    It downloads repositories as tar.gz archives from the Nexus repository.
    Note: Git operations (checkout, add, pull, commit, push) are not supported
    as Nexus stores repositories as static archives.

    Attributes:
        domain (str): Domain of the Nexus instance.
        repository (str): Name of the Nexus repository.
        auth (HttpAuthBase | None): HTTP authentication object for API requests.
        name (str): Name of the versioner.
        base_url (str): Base URL of the Nexus instance.

    """

    def __init__(
        self, domain: str, repository: str, auth: HttpAuthBase | None = None
    ) -> None:
        """Initialize the Nexus versioner.

        Args:
            domain: Domain of the Nexus instance (e.g., "example.com").
            repository: Name of the Nexus repository.
            auth: HTTP authentication object for API requests.
                If None, operations will use public access only.

        """
        self.domain = domain
        self.repository = repository
        self.auth = auth
        self.name = "nexus"
        self.base_url = f"https://{domain}"

    def _get_auth(self) -> HttpAuthBase | None:
        """Get the HTTP authentication object for API requests.

        Returns:
            HttpAuthBase | None: The authentication object or None.

        """
        return self.auth

    async def clone(self, repository_url: str, target_path: str | Path) -> None:
        """Clone a repository from Nexus to the specified path.

        Args:
            repository_url: Name of the repository to clone (not a URL for Nexus).
            target_path: Local path where the repository should be cloned.

        Raises:
            VersionerError: If the clone operation fails.

        """
        target_path = Path(target_path)

        try:
            await self._download_repository(repository_url, target_path)
            logger.info(
                "Successfully cloned repository '%s' to %s", repository_url, target_path
            )
        except Exception as e:
            error_msg = f"Failed to clone repository '{repository_url}': {e}"
            raise VersionerError(error_msg) from e

    async def checkout(self, _repository_path: str | Path, _branch: str) -> None:
        """Checkout a specific branch in the repository.

        Note: Checkout is not supported for Nexus repositories as they are
        stored as static archives, not git repositories.

        Args:
            repository_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            VersionerError: Always raised as checkout is not supported.

        """
        error_msg = "Checkout not supported for Nexus repositories (static archives)"
        raise VersionerError(error_msg)

    async def select_branch(
        self, _repository_path: str | Path, _branches: list[str]
    ) -> str | None:
        """Select the first available branch from a list of branches.

        Note: Branch selection is not supported for Nexus repositories as they are
        stored as static archives, not git repositories.

        Args:
            repository_path: Path to the local repository.
            branches: List of branch names to try in order.

        Returns:
            str | None: Always None as branch selection is not supported.

        Raises:
            VersionerError: Always raised as branch selection is not supported.

        """
        error_msg = (
            "Branch selection not supported for Nexus repositories (static archives)"
        )
        raise VersionerError(error_msg)

    async def add(
        self,
        _repository_path: str | Path,
        _files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area.

        Note: Git operations are not supported for Nexus repositories as they are
        stored as static archives, not git repositories.

        Args:
            repository_path: Path to the local repository.
            files: List of files to add. If None, adds all changes.

        Raises:
            VersionerError: Always raised as git operations are not supported.

        """
        error_msg = (
            "Git operations not supported for Nexus repositories (static archives)"
        )
        raise VersionerError(error_msg)

    async def pull(self, repository_path: str | Path, _branch: str) -> None:
        """Pull latest changes from the remote repository.

        For Nexus repositories, this is equivalent to cloning the latest version
        since repositories are stored as static archives.

        Args:
            repository_path: Path to the local repository.
            _branch: Branch to pull from (ignored for Nexus repositories).

        Raises:
            VersionerError: If the pull operation fails.

        """
        try:
            # For Nexus, pull is equivalent to clone - get the latest version
            # Extract repository name from the path
            repo_path = Path(repository_path)
            repo_name = repo_path.name

            # Clone the latest version to the same location
            await self.clone(repo_name, repository_path)
            logger.info(
                "Successfully pulled latest version of repository '%s' to %s",
                repo_name,
                repository_path,
            )
        except Exception as e:
            error_msg = f"Failed to pull latest changes: {e}"
            raise VersionerError(error_msg) from e

    async def commit(self, _repository_path: str | Path, _message: str) -> None:
        """Commit staged changes.

        Note: Git operations are not supported for Nexus repositories as they are
        stored as static archives, not git repositories.

        Args:
            repository_path: Path to the local repository.
            message: Commit message.

        Raises:
            VersionerError: Always raised as git operations are not supported.

        """
        error_msg = (
            "Git operations not supported for Nexus repositories (static archives)"
        )
        raise VersionerError(error_msg)

    async def push(self, _repository_path: str | Path, _branch: str) -> None:
        """Push commits to the remote repository.

        Note: Git operations are not supported for Nexus repositories as they are
        stored as static archives, not git repositories.

        Args:
            repository_path: Path to the local repository.
            _branch: Branch to push to (ignored for Nexus repositories).

        Raises:
            VersionerError: Always raised as git operations are not supported.

        """
        error_msg = (
            "Git operations not supported for Nexus repositories (static archives)"
        )
        raise VersionerError(error_msg)

    async def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using Nexus API.

        Args:
            repository_url: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            return await self._check_nexus_repository_exists(repository_url)
        except Exception:
            return False

    async def _download_repository(self, repo_name: str, target_path: Path) -> None:
        """Download a repository from Nexus.

        Args:
            repo_name: Name of the repository to download.
            target_path: Target path for the downloaded repository.

        Raises:
            VersionerError: If the repository is not found or download fails.

        """
        # Check if repository exists
        if not await self._check_nexus_repository_exists(repo_name):
            error_msg = f"Repository '{repo_name}' not found in Nexus"
            raise VersionerError(error_msg)

        # Create target directory
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Create FileInfo object for the repository
        file_info = FileInfo(
            name=repo_name,
            host=f"{self.domain}",
            repository=self.repository,
            branch="master",  # Nexus doesn't use branches
        )

        logger.info("Downloading repository '%s' from Nexus", repo_name)

        try:
            # Use streaming download and extract for minimal RAM usage
            auth = self._get_auth()
            auth_obj = auth.get_auth() if auth else None

            # Run optimized download and extract
            optimized_download_and_extract(
                url=file_info.url,
                target_dir=target_path.parent,
                auth_obj=auth_obj,
            )

        except Exception as e:
            error_msg = f"Failed to download repository '{repo_name}': {e}"
            raise VersionerError(error_msg) from e

    async def _check_nexus_repository_exists(self, repo_name: str) -> bool:
        """Check if a repository exists in Nexus using HEAD request on the file.

        Args:
            repo_name: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            # Build the direct file URL
            file_url = (
                f"https://{self.domain}/repository/{self.repository}/{repo_name}.tar.gz"
            )

            auth = self._get_auth()
            auth_obj = auth.get_auth() if auth else None

            async with httpx.AsyncClient() as client:
                response = await client.head(file_url, auth=auth_obj)
                return response.status_code == HTTP_OK

        except Exception:
            return False

    async def stash(
        self, _repository_path: str | Path, _message: str | None = None
    ) -> bool:
        """Stash is not supported for Nexus versioner.

        Args:
            repository_path: Path to the local repository.
            message: Optional stash message.

        Returns:
            bool: Always returns False as stash is not supported.

        Raises:
            VersionerError: Always raises as stash is not supported.

        """
        error_msg = "Stash operation is not supported for Nexus versioner"
        raise VersionerError(error_msg)

    async def safe_pull(
        self, _repository_path: str | Path, _branch: str
    ) -> None:
        """Safe pull is not supported for Nexus versioner.

        Args:
            repository_path: Path to the local repository.
            _branch: Branch to pull from (ignored for Nexus repositories).

        Raises:
            VersionerError: Always raises as safe pull is not supported.

        """
        error_msg = "Safe pull operation is not supported for Nexus versioner"
        raise VersionerError(error_msg)
