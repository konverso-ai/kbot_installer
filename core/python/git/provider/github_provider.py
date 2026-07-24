"""GitHub provider for repository operations.

This module implements the GithubProvider class that handles repository
operations specific to GitHub repositories, using a Versioner (dulwich by
default) for the actual git operations.
"""

from auth.base import HttpAuthBase
from git.provider.git_provider_base import GitProviderBase
from git.versioner import VersionerBase
from utils.Logger import logger

log = logger.get_package_logger("git.provider")


class GithubProvider(GitProviderBase):
    """Provider for GitHub repository operations.

    Attributes:
        base_url (str): Base URL of the GitHub instance.
        account_name (str): Name of the GitHub account.
        auth (HttpAuthBase | None): Authentication object for repository operations.

    """

    name = "github"
    ssh_host = "github.com"
    base_url = "https://{name}.com/{account_name}/{repository_name}.git"

    def __init__(
        self,
        account_name: str = "konverso-ai",
        auth: HttpAuthBase | None = None,
        versioner: VersionerBase | None = None,
    ) -> None:
        """Initialize the GitHub provider.

        Args:
            account_name: Name of the GitHub account.
            auth: HTTP authentication object for repository operations.
                If None, operations will use public access only.
            versioner: Versioner to use for git operations. If None, a
                dulwich-backed versioner is created lazily using ``auth``.

        """
        log.debug("Initializing GitHub provider with account name: %s", account_name)
        super().__init__(account_name, auth, versioner)
