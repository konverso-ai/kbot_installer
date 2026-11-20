"""Errors raised by versioner implementations."""


class VersionerError(Exception):
    """Base exception for versioner-related errors.

    This exception is raised when versioner operations fail.
    """


class RepositoryNotFoundError(VersionerError):
    """Raised when a local repository cannot be opened.

    Catch this to handle both "the path does not exist" and "the path is not a
    git repository" in one place; catch the subclasses to tell them apart.
    """


class NoSuchRepositoryPathError(RepositoryNotFoundError):
    """Raised when the repository path does not exist on the filesystem."""


class NotAGitRepositoryError(RepositoryNotFoundError):
    """Raised when the path exists but does not contain a git repository."""


class BranchNotFoundError(VersionerError):
    """Raised when a requested branch exists neither locally nor on the remote."""


class RemoteNotFoundError(VersionerError):
    """Raised when the repository has no remote under the requested name."""


class DetachedHeadError(VersionerError):
    """Raised when an operation requires a branch but HEAD is detached."""


class MergeConflictError(VersionerError):
    """Raised when a merge leaves conflicts in the working tree.

    The repository is left as the merge produced it: the conflicted paths are
    listed in ``conflicts`` so the caller can report them for manual resolution.
    """

    def __init__(self, message: str, conflicts: list[str] | None = None) -> None:
        """Record the conflicted paths alongside the message.

        Args:
            message: Human-readable description of the failure.
            conflicts: Repository-relative paths left conflicted.

        """
        super().__init__(message)
        self.conflicts = conflicts or []
