"""Bitbucket provider for repository operations.

This module implements the BitbucketProvider class that handles repository
operations specific to Bitbucket repositories, using a Versioner (dulwich by
default) for the actual git operations.
"""

from typing import ClassVar

from git.provider.provider_mixin import ProviderMixin


class BitbucketProvider(ProviderMixin):
    """Provider for Bitbucket repository operations.

    Attributes:
        base_url (str): Base URL of the Bitbucket instance.
        account_name (str): Name of the Bitbucket account.

    """

    name = "bitbucket"
    ssh_host = "bitbucket.org"
    base_url = "https://{name}.org/{account_name}/{repository_name}.git"
    default_branches: ClassVar[list[str]] = ["master", "dev"]
