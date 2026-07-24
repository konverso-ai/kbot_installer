"""Base class for git-backed repository providers (GitHub, Bitbucket).

Unlike a mixin, this is a plain concrete base class: a provider *has a*
``Versioner`` (injected or lazily created) and *is a* ``ProviderBase``. There
is no shared "bag of git operations" grafted onto unrelated classes.
"""

from pathlib import Path

from typing_extensions import override

from auth.base import HttpAuthBase
from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.url import build_git_url
from git.versioner import (
    VersionerBase,
    VersionerError,
    create_versioner,
)


class GitProviderBase(ProviderBase):
    """Provider for repositories reachable over plain git (HTTPS or SSH).

    Concrete subclasses (``GithubProvider``, ``BitbucketProvider``) only need
    to set the ``name``, ``ssh_host`` and ``base_url`` class attributes.

    Attributes:
        name: Provider name (e.g. ``"github"``).
        ssh_host: Hostname used to build SSH repository URLs.
        base_url: HTTPS URL template with ``{name}``, ``{account_name}`` and
            ``{repository_name}`` placeholders.

    """

    name: str = ""
    ssh_host: str = ""
    base_url: str = ""

    def __init__(
        self,
        account_name: str,
        auth: HttpAuthBase | None = None,
        versioner: VersionerBase | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            account_name: Name of the account or organization owning the
                repository.
            auth: Authentication object for repository operations. If None,
                operations use public access only.
            versioner: Versioner to use for git operations. If None, a
                ``dulwich``-backed versioner is created lazily using ``auth``.

        """
        self.account_name = account_name
        self._auth = auth
        self._versioner = versioner
        self.branch_used: str | None = None

    def _get_auth(self) -> HttpAuthBase | None:
        """Return the authentication object configured for this provider."""
        return self._auth

    def _get_versioner(self) -> VersionerBase:
        """Return the versioner, creating a default dulwich one if needed.

        Returns:
            The versioner instance used for git operations.

        """
        if self._versioner is None:
            self._versioner = create_versioner("dulwich", auth=self._get_auth())
        return self._versioner

    def build_repository_url(self, repository_name: str) -> str:
        """Build the remote repository URL for the configured auth mode.

        Args:
            repository_name: Short repository name.

        Returns:
            HTTPS or SSH URL depending on the active authentication.

        Raises:
            ValueError: If the provider is missing URL template attributes.

        """
        return build_git_url(
            name=self.name,
            account_name=self.account_name,
            repository_name=repository_name,
            base_url=self.base_url,
            ssh_host=self.ssh_host,
            auth=self._get_auth(),
        )

    @override
    def clone_and_checkout(
        self,
        target_path: str | Path,
        branch: str | None = None,
        *,
        repository_url: str | None = None,
        repository_name: str | None = None,
        commit: str | None = None,
    ) -> None:
        """Clone a repository to the specified path and optionally checkout a branch.

        Args:
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no
                checkout is performed.
            repository_url: URL of the repository to clone. Mutually
                exclusive with ``repository_name``.
            repository_name: Name of the repository to clone; the URL is
                built from the provider's account/base URL configuration.
            commit: Unused by plain git clones; commit pinning is not
                supported for branch checkouts.

        Raises:
            ValueError: If neither ``repository_url`` nor ``repository_name``
                is provided.
            ProviderError: If the clone operation fails.

        """
        if repository_url is None:
            if repository_name is None:
                msg = "repository_url or repository_name is required"
                raise ValueError(msg)
            repository_url = self.build_repository_url(repository_name)

        versioner = self._get_versioner()
        try:
            if branch:
                versioner.clone(repository_url, target_path, branch=branch, depth=1)
            else:
                versioner.clone(repository_url, target_path)
            self.branch_used = branch
        except VersionerError as e:
            error_msg = f"Failed to clone repository '{repository_url}': {e}"
            raise ProviderError(error_msg) from e

    def list_remote_branches(self, repository_url: str) -> list[str]:
        """List branches available on the remote repository.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            Branch names reported by the versioner.

        Raises:
            ProviderError: If the remote cannot be queried.

        """
        try:
            return self._get_versioner().list_remote_branches(repository_url)
        except VersionerError as e:
            error_msg = f"Failed to list remote branches for '{repository_url}': {e}"
            raise ProviderError(error_msg) from e

    def checkout_branch(self, target_path: str | Path, branch: str) -> None:
        """Checkout a branch in an already cloned repository.

        Args:
            target_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            ProviderError: If checkout fails.

        """
        try:
            self._get_versioner().checkout(target_path, branch)
            self.branch_used = branch
        except VersionerError as e:
            error_msg = f"Failed to checkout branch '{branch}' for '{target_path}': {e}"
            raise ProviderError(error_msg) from e

    @override
    def check_remote_repository_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists.

        Args:
            repository_name: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            repository_url = self.build_repository_url(repository_name)
            return self._get_versioner().remote_exists(repository_url)
        except Exception:
            return False

    @override
    def get_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Name of the provider.

        """
        return self.name

    @override
    def get_branch(self) -> str:
        """Get the branch used during the last clone or checkout.

        Returns:
            str: Branch of the provider. Returns empty string if no branch
            was used.

        """
        return self.branch_used or ""
