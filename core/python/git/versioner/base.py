"""Base versioner class for full git operations.

This module defines the abstract base class that all versioners
must implement to provide a unified interface for full git operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from git.auth_protocol import GitAuthProtocol
from git.versioner.author import Author
from git.versioner.pull_result import PullResult
from git.versioner.status import RepoStatus

__all__ = ["VersionerBase"]


class VersionerBase(ABC):
    """Abstract base class for versioners.

    This class defines the interface that all versioners must implement.
    It provides methods for full git operations: clone, add, pull, commit, and push,
    plus read-only inspection of a local repository.

    Attributes:
        name (str): Name of the versioner.
        base_url (str): Base URL of the versioner.

    """

    @abstractmethod
    def _get_auth(self) -> GitAuthProtocol | None:
        """Get the authentication object for git operations.

        Returns:
            GitAuthProtocol | None: The authentication object or None.

        """

    #
    # Read-only inspection
    #

    @abstractmethod
    def head_commit_id(self, repository_path: str | Path) -> str:
        """Return the full commit id (SHA-1) currently pointed to by HEAD.

        Args:
            repository_path: Path to the local repository.

        Returns:
            The 40-character hexadecimal commit id.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            VersionerError: If HEAD cannot be resolved (e.g. empty repository).

        """

    @abstractmethod
    def current_branch(self, repository_path: str | Path) -> str:
        """Return the name of the branch currently checked out.

        Args:
            repository_path: Path to the local repository.

        Returns:
            The short branch name (without the ``refs/heads/`` prefix).

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            DetachedHeadError: If HEAD does not point to a local branch.

        """

    @abstractmethod
    def describe_head(self, repository_path: str | Path) -> str:
        """Return a human-readable name for HEAD, even when detached.

        Falls back to the name of a tag pointing at HEAD, then to the
        abbreviated commit id, so callers can display a meaningful label
        without having to handle :class:`DetachedHeadError` themselves.

        Args:
            repository_path: Path to the local repository.

        Returns:
            The branch name, a tag name, or the 7-character commit id.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            VersionerError: If the repository has no commit yet.

        """

    @abstractmethod
    def read_file(
        self,
        repository_path: str | Path,
        file_path: str,
        revision: str = "HEAD",
    ) -> bytes | None:
        """Return the content of a tracked file at a given revision.

        Replaces GitPython's ``diff_item.a_blob.data_stream.read()``, used to
        show the committed version of a locally modified file.

        Args:
            repository_path: Path to the local repository.
            file_path: Repository-relative path of the file.
            revision: Commit, branch or tag to read the file from.

        Returns:
            The file content, or None if the path does not exist at that
            revision.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            VersionerError: If the revision is unknown.

        """

    @abstractmethod
    def remote_url(self, repository_path: str | Path, remote: str = "origin") -> str:
        """Return the configured URL of a remote.

        Args:
            repository_path: Path to the local repository.
            remote: Name of the remote to look up.

        Returns:
            The remote URL, as stored in the repository configuration.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            RemoteNotFoundError: If no such remote is configured.

        """

    @abstractmethod
    def status(self, repository_path: str | Path) -> RepoStatus:
        """Return the staged, unstaged and untracked paths of the repository.

        Args:
            repository_path: Path to the local repository.

        Returns:
            A :class:`RepoStatus` snapshot with repository-relative paths.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            VersionerError: If the status cannot be computed.

        """

    @abstractmethod
    def is_bare(self, repository_path: str | Path) -> bool:
        """Return whether the repository is bare (has no working tree).

        Args:
            repository_path: Path to the local repository.

        Returns:
            True if the repository is bare.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.

        """

    @abstractmethod
    def working_dir(self, repository_path: str | Path) -> str:
        """Return the absolute path of the repository working tree.

        Args:
            repository_path: Path to the local repository.

        Returns:
            The working tree path.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            VersionerError: If the repository is bare.

        """

    @abstractmethod
    def ahead_behind(
        self, repository_path: str | Path, branch: str | None = None
    ) -> tuple[int, int]:
        """Count commits the local branch is ahead of and behind its remote.

        Replaces parsing the English output of ``git status`` for the
        ``"git pull"`` / ``"git push"`` hints.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to compare. Defaults to the current branch.

        Returns:
            A ``(ahead, behind)`` tuple. ``(0, 0)`` when the remote-tracking
            branch is unknown, so callers treat it as "nothing pending".

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.
            BranchNotFoundError: If the local branch does not exist.

        """

    @abstractmethod
    def list_local_branches(self, repository_path: str | Path) -> list[str]:
        """List local branch names present in the repository.

        Args:
            repository_path: Path to the local repository.

        Returns:
            Sorted unique local branch names.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.

        """

    @abstractmethod
    def list_remote_tracking_branches(self, repository_path: str | Path) -> list[str]:
        """List the branch names of the ``origin`` remote known locally.

        Reads the ``refs/remotes/origin/*`` refs as of the last fetch, without
        contacting the remote.

        Args:
            repository_path: Path to the local repository.

        Returns:
            Sorted unique branch names, without the ``HEAD`` symbolic ref.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.

        """

    @abstractmethod
    def default_remote_branch(self, repository_path: str | Path) -> str | None:
        """Return the default branch of ``origin``, as recorded by the clone.

        Args:
            repository_path: Path to the local repository.

        Returns:
            The branch ``refs/remotes/origin/HEAD`` points to, or None if it is unknown.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.

        """

    #
    # Write operations
    #

    @abstractmethod
    def add(
        self,
        repository_path: str | Path,
        files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area.

        When ``files`` is None every change is staged, including deletions,
        matching ``git add --all``.

        Args:
            repository_path: Path to the local repository.
            files: Repository-relative (or absolute) paths to add. If None,
                adds all changes.

        Raises:
            VersionerError: If the add operation fails.

        """

    @abstractmethod
    def remove(self, repository_path: str | Path, files: list[str]) -> None:
        """Remove files from the index and from the working tree.

        Equivalent to ``git rm``; replaces GitPython's
        ``index.remove(files, working_tree=True)``.

        Args:
            repository_path: Path to the local repository.
            files: Repository-relative (or absolute) paths to remove.

        Raises:
            VersionerError: If a path does not match a tracked file, or if the
                removal fails.

        """

    @abstractmethod
    def unstage(self, repository_path: str | Path, files: list[str]) -> None:
        """Remove files from the index while keeping the working tree intact.

        Equivalent to ``git reset HEAD -- <files>``.

        Args:
            repository_path: Path to the local repository.
            files: Repository-relative (or absolute) paths to unstage.

        Raises:
            VersionerError: If the unstage operation fails.

        """

    @abstractmethod
    def restore_files(self, repository_path: str | Path, files: list[str]) -> None:
        """Restore working tree files from the index, discarding local edits.

        Equivalent to ``git restore -- <files>``; replaces GitPython's
        ``index.checkout(files, force=True)``.

        Args:
            repository_path: Path to the local repository.
            files: Repository-relative (or absolute) paths to restore.

        Raises:
            VersionerError: If the restore operation fails.

        """

    @abstractmethod
    def reset_hard(self, repository_path: str | Path, treeish: str = "HEAD") -> None:
        """Reset HEAD, the index and the working tree to ``treeish``.

        Equivalent to ``git reset --hard <treeish>``. Discards local changes.

        Args:
            repository_path: Path to the local repository.
            treeish: Commit, tag or branch to reset to.

        Raises:
            VersionerError: If the reset operation fails.

        """

    @abstractmethod
    def create_tag(
        self,
        repository_path: str | Path,
        tag_name: str,
        message: str | None = None,
    ) -> None:
        """Create a tag pointing at the current HEAD.

        Args:
            repository_path: Path to the local repository.
            tag_name: Name of the tag to create.
            message: Optional message. When provided an annotated tag is
                created, otherwise a lightweight one.

        Raises:
            VersionerError: If the tag already exists or cannot be created.

        """

    @abstractmethod
    def list_tags(self, repository_path: str | Path) -> list[str]:
        """List tag names present in the repository.

        Args:
            repository_path: Path to the local repository.

        Returns:
            Sorted tag names.

        Raises:
            RepositoryNotFoundError: If the repository cannot be opened.

        """

    @abstractmethod
    def remote_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using the most efficient method.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            bool: True if repository exists, False otherwise.

        """

    @abstractmethod
    def checkout(self, repository_path: str | Path, branch: str) -> None:
        """Checkout a specific branch in the repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """

    @abstractmethod
    def clone(
        self,
        repository_url: str,
        target_path: str | Path,
        *,
        branch: str | None = None,
        depth: int | None = None,
    ) -> object:
        """Clone a repository to the specified path.

        Implementations fetch every remote branch (not just ``branch``) so
        that callers can later use :meth:`checkout` to switch to another
        branch without cloning again; ``branch`` only selects which one is
        checked out as HEAD.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Optional branch to check out as HEAD after cloning. If
                None, the repository's default branch is checked out.
            depth: Optional shallow clone depth.

        Returns:
            A backend-specific handle to the freshly cloned repository, so
            callers can cache it and avoid re-cloning when trying alternate
            branches.

        Raises:
            VersionerError: If the clone operation fails.

        """

    @abstractmethod
    def list_remote_branches(self, repository_url: str) -> list[str]:
        """List branch names available on the remote repository.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            Sorted unique branch names reported by the remote.

        Raises:
            VersionerError: If the remote cannot be queried.

        """

    @abstractmethod
    def commit(
        self,
        repository_path: str | Path,
        message: str,
        author: Author | None = None,
    ) -> str | None:
        """Commit staged changes.

        Args:
            repository_path: Path to the local repository.
            message: Commit message.
            author: Identity to record as author and committer. Defaults to
                the versioner's configured author.

        Returns:
            The new commit id, or None when there was nothing staged to commit.

        Raises:
            VersionerError: If the commit operation fails.

        """

    @abstractmethod
    def fetch(self, repository_path: str | Path) -> None:
        """Fetch latest changes from the remote repository.

        Args:
            repository_path: Path to the local repository.

        Raises:
            VersionerError: If the fetch operation fails.

        """

    @abstractmethod
    def pull(self, repository_path: str | Path, branch: str) -> PullResult:
        """Pull latest changes from the remote repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Returns:
            The paths added, modified and deleted by the pull.

        Raises:
            VersionerError: If the pull operation fails.

        """

    @abstractmethod
    def push(self, repository_path: str | Path, branch: str) -> None:
        """Push commits to the remote repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to push to.

        Raises:
            VersionerError: If the push operation fails.

        """

    @abstractmethod
    def push_branches(self, repository_path: str | Path, branches: list[str]) -> None:
        """Push multiple branches to the remote in a single operation.

        Args:
            repository_path: Path to the local repository.
            branches: Local branch names to push to same-named remote branches.

        Raises:
            VersionerError: If the push operation fails.

        """

    @abstractmethod
    def safe_pull(self, repository_path: str | Path, branch: str) -> PullResult:
        """Safely pull latest changes, stashing any local changes first.

        This method performs a safe pull by:
        1. Stashing any local changes
        2. Pulling the latest changes from remote
        3. Applying the stashed changes back

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Returns:
            The paths added, modified and deleted by the pull.

        Raises:
            VersionerError: If the safe pull operation fails.

        """

    @abstractmethod
    def select_branch(
        self, repository_path: str | Path, branches: list[str]
    ) -> str | None:
        """Select the first available branch from a list of branches.

        This method attempts to checkout each branch in the provided list
        until it finds one that exists and can be checked out successfully.
        It stops at the first successful checkout and returns the branch name.

        Args:
            repository_path: Path to the local repository.
            branches: List of branch names to try in order.

        Returns:
            str | None: The name of the first successfully checked out branch,
                or None if no branch could be checked out.

        Raises:
            VersionerError: If there's an error with the repository or versioner.

        """

    @abstractmethod
    def stash(self, repository_path: str | Path, message: str | None = None) -> bool:
        """Stash current changes in the repository.

        Args:
            repository_path: Path to the local repository.
            message: Optional stash message. If None, uses default message.

        Returns:
            bool: True if changes were stashed, False if no changes to stash.

        Raises:
            VersionerError: If the stash operation fails.

        """
