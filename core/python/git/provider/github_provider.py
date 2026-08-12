"""GitHub provider for repository operations.

This module implements the GithubProvider class that handles repository
operations specific to GitHub repositories, using a Versioner (dulwich by
default) for the actual git operations.
"""

from typing import ClassVar

from git.provider.provider_mixin import ProviderMixin


class GithubProvider(ProviderMixin):
    """Provider for GitHub repository operations.

    Attributes:
        base_url (str): Base URL of the GitHub instance.
        account_name (str): Name of the GitHub account.

    """

    name = "github"
    ssh_host = "github.com"
    base_url = "https://{name}.com/{account_name}/{repository_name}.git"
    default_branches: ClassVar[list[str]] = ["main", "dev"]
