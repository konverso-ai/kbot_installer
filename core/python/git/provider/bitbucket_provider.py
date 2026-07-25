"""Bitbucket provider for repository operations.

This module implements the BitbucketProvider class that handles repository
operations specific to Bitbucket repositories, using a Versioner (dulwich by
default) for the actual git operations.
"""

from git.auth_protocol import GitAuthProtocol
from git.provider.git_provider_base import GitProviderBase
from git.versioner import VersionerBase


class BitbucketProvider(GitProviderBase):
    """Provider for Bitbucket repository operations.

    Attributes:
        base_url (str): Base URL of the Bitbucket instance.
        account_name (str): Name of the Bitbucket account.
        auth (GitAuthProtocol | None): Authentication object for repository operations.

    """

    name = "bitbucket"
    ssh_host = "bitbucket.org"
    base_url = "https://{name}.org/{account_name}/{repository_name}.git"

    def __init__(
        self,
        account_name: str = "konversoai",
        auth: GitAuthProtocol | None = None,
        versioner: VersionerBase | None = None,
        **kwargs,  # noqa: ARG002
    ) -> None:
        """Initialize the Bitbucket provider.

        Args:
            account_name: Name of the Bitbucket account.
            auth: HTTP authentication object for repository operations.
                If None, operations will use public access only.
            versioner: Versioner to use for git operations. If None, a
                dulwich-backed versioner is created lazily using ``auth``.
            **kwargs: Additional arguments (ignored).

        """
        super().__init__(account_name, auth, versioner)
