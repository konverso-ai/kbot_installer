"""Mixin for versioner operations that are not supported by a backend."""

from pathlib import Path
from typing import ClassVar

from typing_extensions import override

from git.versioner.base import VersionerBase, VersionerError


class UnsupportedOpsMixin(VersionerBase):
    """Mixin providing default VersionerBase methods that raise VersionerError.

    Subclasses inherit this mixin and implement only the operations their
    backend actually supports. Unsupported operations raise VersionerError
    with messages defined by the class attributes below.

    """

    git_ops_unsupported: ClassVar[str] = "Git operations not supported"
    checkout_unsupported: ClassVar[str] = "Checkout not supported"
    select_branch_unsupported: ClassVar[str] = "Branch selection not supported"
    stash_unsupported: ClassVar[str] = "Stash not supported"
    safe_pull_unsupported: ClassVar[str] = "Safe pull not supported"

    @override
    def add(
        self,
        _repository_path: str | Path,
        _files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area."""
        raise VersionerError(self.git_ops_unsupported)

    @override
    def fetch(self, _repository_path: str | Path) -> None:
        """Fetch latest changes from the remote repository."""
        raise VersionerError(self.git_ops_unsupported)

    @override
    def commit(self, _repository_path: str | Path, _message: str) -> None:
        """Commit staged changes."""
        raise VersionerError(self.git_ops_unsupported)

    @override
    def push(self, _repository_path: str | Path, _branch: str) -> None:
        """Push commits to the remote repository."""
        raise VersionerError(self.git_ops_unsupported)

    @override
    def push_branches(self, _repository_path: str | Path, _branches: list[str]) -> None:
        """Push multiple branches to the remote in a single operation."""
        raise VersionerError(self.git_ops_unsupported)

    @override
    def checkout(self, _repository_path: str | Path, _branch: str) -> None:
        """Checkout a specific branch in the repository."""
        raise VersionerError(self.checkout_unsupported)

    @override
    def select_branch(
        self, _repository_path: str | Path, _branches: list[str]
    ) -> str | None:
        """Select the first available branch from a list of branches."""
        raise VersionerError(self.select_branch_unsupported)

    @override
    def stash(self, _repository_path: str | Path, _message: str | None = None) -> bool:
        """Stash current changes in the repository."""
        raise VersionerError(self.stash_unsupported)

    @override
    def safe_pull(self, _repository_path: str | Path, _branch: str) -> None:
        """Safely pull latest changes, stashing any local changes first."""
        raise VersionerError(self.safe_pull_unsupported)
