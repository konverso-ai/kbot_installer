"""Versioner package for full git operations.

This package provides a unified interface for full git operations
including clone, add, pull, commit, and push, plus read-only inspection
of a local repository.
"""

from git.versioner.author import Author
from git.versioner.factory import add_versioner
from git.versioner.base import VersionerBase
from git.versioner.errors import (
    BranchNotFoundError,
    DetachedHeadError,
    MergeConflictError,
    NoSuchRepositoryPathError,
    NotAGitRepositoryError,
    RemoteNotFoundError,
    RepositoryNotFoundError,
    VersionerError,
)
from git.versioner.pull_result import PullResult
from git.versioner.status import RepoStatus

__all__ = [
    "Author",
    "BranchNotFoundError",
    "DetachedHeadError",
    "MergeConflictError",
    "NoSuchRepositoryPathError",
    "NotAGitRepositoryError",
    "PullResult",
    "RemoteNotFoundError",
    "RepoStatus",
    "RepositoryNotFoundError",
    "VersionerBase",
    "VersionerError",
    "add_versioner",
]
