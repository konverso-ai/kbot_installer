"""Nexus provider for repository operations.

This module implements the NexusProvider class that handles repository
operations specific to Nexus repositories using the Nexus API.
"""

import logging
from pathlib import Path

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase
from kbot_installer.core.provider.provider_base import ProviderBase, ProviderError
from kbot_installer.core.utils import (
    optimized_download_and_extract_ter,
)

logger = logging.getLogger(__name__)


class NexusProvider(ProviderBase):
    """Provider for Nexus repository operations.

    This provider handles operations on Nexus repositories using the Nexus API.
    It downloads repositories as tar.gz archives from the Nexus repository.

    Attributes:
        base_url (str): Base URL of the Nexus instance.
        domain (str): Domain of the Nexus instance.
        repository (str): Name of the Nexus repository.
        auth (HttpAuthBase | None): HTTP authentication object for API requests.

    """

    name = "nexus"
    base_url = "https://{domain}"
    branch = "master"

    def __init__(
        self, domain: str, repository: str, auth: HttpAuthBase | None = None
    ) -> None:
        """Initialize the Nexus provider.

        Args:
            domain: Domain of the Nexus instance (e.g., "example.com").
            repository: Name of the Nexus repository.
            auth: HTTP authentication object for API requests.
                If None, operations will use public access only.

        """
        self.base_url = self.base_url.format(domain=domain)
        self.domain = domain
        self.repository = repository
        self._auth = auth
        # Store the branch that was successfully used
        self.branch_used: str | None = None

    def _get_auth(self) -> HttpAuthBase | None:
        """Get the HTTP authentication object for API requests.

        Returns:
            HttpAuthBase | None: The authentication object or None.

        """
        return self._auth

    def _build_nexus_url(self, repo_name: str, branch: str | None = None) -> str:
        """Build the Nexus API URL for downloading a repository.

        Args:
            repo_name: Name of the repository to download.
            branch: Branch to download. If None, uses "master".

        Returns:
            str: The complete Nexus API URL.

        """
        branch = branch or "master"
        # URL correcte pour Nexus avec branch et nom complet du fichier
        return f"https://{self.domain}/repository/{self.repository}/{branch}/{repo_name}/{repo_name}_latest.tar.gz"

    def clone_and_checkout(
        self, repository_name: str, target_path: str | Path, branch: str | None = None
    ) -> None:
        """Clone a repository from Nexus and optionally checkout a branch.

        Args:
            repository_name: Name of the repository to clone (not a URL for Nexus).
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no checkout is performed.

        Raises:
            ProviderError: If the clone operation fails.

        """
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Downloading repository '%s' from Nexus with streaming", repository_name
        )

        try:
            # Use streaming download and extract for minimal RAM usage
            auth = self._get_auth()
            auth_obj = auth.get_auth() if auth else None

            # Build the correct Nexus URL
            branch_to_use = branch or "master"
            nexus_url = self._build_nexus_url(repository_name, branch_to_use)

            # Store the branch that was successfully used
            self.branch_used = branch_to_use

            # Run streaming download and extract directly with the correct URL
            # Extract to parent directory so the tar.gz can create the repository folder
            optimized_download_and_extract_ter(nexus_url, target_path.parent, auth_obj)

            logger.info(
                "Successfully cloned repository '%s' to %s",
                repository_name,
                target_path,
            )

        except Exception as e:
            # Build the URL that was attempted
            nexus_url = self._build_nexus_url(repository_name, branch)
            error_msg = (
                f"Failed to clone repository '{repository_name}' from {nexus_url}: {e}"
            )
            raise ProviderError(error_msg) from e

    async def check_remote_repository_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists on Nexus.

        Args:
            repository_name: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            # Use the versioner to check if repository exists
            versioner = self._get_versioner()
            return await versioner.check_remote_repository_exists(repository_name)
        except Exception:
            return False

    def get_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Name of the provider.

        """
        return self.name

    def get_branch(self) -> str:
        """Get the branch of the provider.

        Returns:
            str: Branch of the provider.

        """
        return self.branch_used or self.branch
