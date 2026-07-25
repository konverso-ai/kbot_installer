"""Provider implementing plain-git repository operations (GitHub, Bitbucket).

``ProviderMixin`` implements ``ProviderBase`` for repositories reachable over
plain git. It is named "mixin" (rather than "base") because it only supplies
behavior shared by concrete providers (``GithubProvider``, ``BitbucketProvider``);
it does not own authentication or versioner construction, both of which are the
caller's responsibility.
"""
from pathlib import Path
from typing import ClassVar

from typing_extensions import override

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.url import build_git_url
from git.versioner import VersionerBase, VersionerError


class ProviderMixin(ProviderBase):
    """Provider for repositories reachable over plain git (HTTPS or SSH).

    Concrete providers (``GithubProvider``, ``BitbucketProvider``) only need
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
    default_branches: ClassVar[list[str]] = []

    def __init__(
        self,
        account_name: str,
        versioner: VersionerBase,
        branches: list[str] | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            account_name: Name of the account or organization owning the
                repository.
            versioner: Versioner to use for git operations, already
                configured with whatever authentication is required.
                Constructing the versioner (and its authentication) is not
                this provider's responsibility.
            branches: Default fallback branches to try, in order, when the
                branch requested in :meth:`clone_and_checkout` is not
                available. Defaults to the class-level ``default_branches``
                value (e.g. ``["main", "dev"]`` for :class:`GithubProvider`)
                when not given.

        """
        self.account_name = account_name
        self._versioner = versioner
        self.branches: list[str] = list(branches) if branches is not None else list(type(self).default_branches)
        self._branch_used: str | None = None

    def _build_repository_url(self, repository_name: str) -> str:
        """Build the remote repository URL for the configured auth mode.

        Args:
            repository_name: Short repository name.

        Returns:
            HTTPS or SSH URL depending on the versioner's authentication.

        Raises:
            ValueError: If the provider is missing URL template attributes.

        """
        return build_git_url(
            name=self.name,
            account_name=self.account_name,
            repository_name=repository_name,
            base_url=self.base_url,
            ssh_host=self.ssh_host,
            auth=self._versioner._get_auth(),  # noqa: SLF001 - internal hook shared within the `git` package
        )

    @override
    def clone_and_checkout(
        self,
        repository_name: str,
        target_path: str | Path,
        *,
        branch: str | None = None,
        commit_id: str | None = None,
    ) -> None:
        """Clone a repository to the specified path and optionally checkout a branch.

        Args:
            repository_name: Name of the repository to clone; the URL is
                built from the provider's account/base URL configuration.
            target_path: Local path where the repository should be cloned.
            branch: Specific branch to checkout after cloning. If None, no
                checkout is performed.
            commit_id: Unused by plain git clones; commit pinning is not
                supported for branch checkouts.

        Raises:
            ProviderError: If the clone operation fails.

        """
        repository_url = self._build_repository_url(repository_name)

        try:
            if branch:
                self._versioner.clone(repository_url, target_path, branch=branch, depth=1)
            else:
                self._versioner.clone(repository_url, target_path)
            self._branch_used = branch
        except VersionerError as e:
            error_msg = f"Failed to clone repository '{repository_url}': {e}"
            raise ProviderError(error_msg) from e

    @override
    def remote_exists(self, repository_name: str) -> bool:
        """Check if a remote repository exists.

        Args:
            repository_name: Name of the repository to check.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            repository_url = self._build_repository_url(repository_name)
            return self._versioner.remote_exists(repository_url)
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
        return self._branch_used or ""
