"""Dulwich versioner for full git operations.

This module implements the DulwichVersioner class that handles full git
operations using Dulwich for any git repository.
"""
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from dulwich import porcelain
from dulwich.diff_tree import CHANGE_ADD, CHANGE_DELETE, CHANGE_MODIFY, tree_changes
from dulwich.errors import GitProtocolError, HangupException, NotGitRepository
from dulwich.graph import find_merge_base
from dulwich.object_store import tree_lookup_path
from dulwich.objectspec import parse_commit
from dulwich.porcelain import Error as DulwichPorcelainError
from dulwich.repo import Repo
from typing_extensions import override

from git.auth_protocol import GitAuthProtocol, RemoteKwargs
from git.versioner.author import Author
from git.versioner.errors import (
    BranchNotFoundError,
    DetachedHeadError,
    MergeConflictError,
    NoSuchRepositoryPathError,
    NotAGitRepositoryError,
    RemoteNotFoundError,
    VersionerError,
)
from git.versioner.pull_result import PullResult
from git.versioner.status import RepoStatus
from git.versioner.str_repr_mixin import StrReprMixin
from utils.Logger import logger

if TYPE_CHECKING:
    from dulwich.objects import Blob
    from dulwich.refs import Ref

log = logger.get_package_logger("git.versioner")

DEFAULT_AUTHOR = Author(name="Git Versioner", email="versioner@example.com")
_LOCAL_BRANCH_PREFIX = b"refs/heads/"
_REMOTE_BRANCH_PREFIX = b"refs/remotes/origin/"
_DULWICH_ERRORS = (
    NotGitRepository,
    GitProtocolError,
    HangupException,
    DulwichPorcelainError,
)


class DulwichVersioner(StrReprMixin):
    """Versioner for git repository operations using Dulwich.

    This versioner handles full git operations on any git repository using Dulwich
    for git operations. It implements the VersionerBase interface and provides
    all necessary git functionality including clone, add, pull, commit, and push.

    Attributes:
        auth (GitAuthProtocol | None): Authentication object for git operations.
        author (Author): Author identity used for commit metadata.

    """

    def __init__(
        self,
        auth: GitAuthProtocol | None = None,
        author: Author = DEFAULT_AUTHOR,
    ) -> None:
        """Initialize the Dulwich versioner.

        Args:
            auth: Authentication object for git operations.
                If None, operations will use public access only.
            author: Author identity used for commit metadata.

        """
        self._auth = auth
        self._author = author

    @override
    def _get_auth(self) -> GitAuthProtocol | None:
        """Get the authentication object for git operations.

        Returns:
            GitAuthProtocol | None: The authentication object or None.

        """
        return self._auth

    def _get_remote_kwargs(self) -> RemoteKwargs:
        """Build Dulwich remote keyword arguments from authentication.

        Returns:
            Keyword arguments for Dulwich network operations (username, password, etc.).

        """
        auth = self._get_auth()
        if auth is None:
            return {}

        return auth.remote_kwargs()

    def _dulwich_remote_kwargs(self) -> dict[str, Any]:
        """Return remote kwargs typed for Dulwich porcelain calls."""
        return cast("dict[str, Any]", self._get_remote_kwargs())

    def _get_repository(self, repository_path: str | Path) -> Repo:
        """Get a Dulwich Repo object from the given path.

        The caller owns the returned repository and must close it. Prefer
        :meth:`_open_repository`, which closes it automatically.

        Args:
            repository_path: Path to the local repository.

        Returns:
            Repo: Repository object.

        Raises:
            NoSuchRepositoryPathError: If the path does not exist.
            NotAGitRepositoryError: If the path is not a git repository.

        """
        repo_path = Path(repository_path)
        if not repo_path.exists():
            error_msg = f"Repository path does not exist: {repo_path}"
            raise NoSuchRepositoryPathError(error_msg)

        try:
            return Repo(str(repo_path))
        except NotGitRepository as e:
            error_msg = f"Failed to open repository at {repository_path}: {e}"
            raise NotAGitRepositoryError(error_msg) from e

    @contextmanager
    def _open_repository(self, repository_path: str | Path) -> Iterator[Repo]:
        """Open a repository and guarantee it is closed afterwards.

        Dulwich keeps packfiles open on the ``Repo`` object; leaving them
        unclosed leaks file descriptors in long-running processes.

        Args:
            repository_path: Path to the local repository.

        Yields:
            Repo: The opened repository.

        Raises:
            NoSuchRepositoryPathError: If the path does not exist.
            NotAGitRepositoryError: If the path is not a git repository.

        """
        repo = self._get_repository(repository_path)
        try:
            yield repo
        finally:
            repo.close()

    @staticmethod
    def _has_working_tree_changes(repo: Repo) -> bool:
        """Return True when the repository has unstaged or untracked changes."""
        status = porcelain.status(repo)
        staged = status.staged
        has_staged = any(staged.get(key) for key in ("add", "delete", "modify"))
        return bool(has_staged or status.unstaged or status.untracked)

    @staticmethod
    def _has_staged_changes(repo: Repo) -> bool:
        """Return True when the index has staged changes."""
        status = porcelain.status(repo)
        staged = status.staged
        return bool(staged.get("add") or staged.get("delete") or staged.get("modify"))

    def _get_current_branch_name(self, repo: Repo) -> str:
        """Return the current branch name from HEAD.

        ``Repo.refs.follow`` returns ``(chain_of_refnames, sha)``; the branch
        ref is the last entry of the chain, not the sha.

        Raises:
            DetachedHeadError: If HEAD does not point to a local branch.

        """
        refnames, _sha = repo.refs.follow(cast("Ref", b"HEAD"))
        branch_ref = refnames[-1] if refnames else None
        if branch_ref is None or not branch_ref.startswith(_LOCAL_BRANCH_PREFIX):
            error_msg = "No current branch found (detached HEAD)"
            raise DetachedHeadError(error_msg)
        return branch_ref[len(_LOCAL_BRANCH_PREFIX) :].decode()

    #
    # Read-only inspection
    #

    @staticmethod
    def _decode_paths(paths: object) -> list[str]:
        """Decode a Dulwich path collection to a list of ``str``.

        Dulwich returns bytes for tracked paths but may return ``str`` for
        untracked ones depending on how the status was computed.
        """
        return [
            path.decode() if isinstance(path, bytes) else path
            for path in cast("list[bytes | str]", paths or [])
        ]

    @override
    def head_commit_id(self, repository_path: str | Path) -> str:
        """Return the full commit id currently pointed to by HEAD."""
        with self._open_repository(repository_path) as repo:
            try:
                return repo.head().decode()
            except KeyError as e:
                error_msg = f"Repository has no HEAD commit: {repository_path}"
                raise VersionerError(error_msg) from e

    @override
    def current_branch(self, repository_path: str | Path) -> str:
        """Return the name of the branch currently checked out."""
        with self._open_repository(repository_path) as repo:
            return self._get_current_branch_name(repo)

    @override
    def describe_head(self, repository_path: str | Path) -> str:
        """Return a human-readable name for HEAD, even when detached."""
        with self._open_repository(repository_path) as repo:
            try:
                return self._get_current_branch_name(repo)
            except DetachedHeadError:
                pass

            head = self._head_sha(repo)
            if head is None:
                error_msg = f"Repository {repository_path} has no commit yet"
                raise VersionerError(error_msg)

            return self._tag_pointing_at(repo, head) or head.decode()[:7]

    @staticmethod
    def _tag_pointing_at(repo: Repo, commit_id: bytes) -> str | None:
        """Return a tag name resolving to ``commit_id``, if any."""
        for tag in porcelain.tag_list(repo):
            ref = b"refs/tags/" + tag
            target = repo.refs[ref]
            obj = repo[target]
            resolved = obj.object[1] if obj.type_name == b"tag" else target
            if resolved == commit_id:
                return tag.decode()
        return None

    @override
    def read_file(
        self,
        repository_path: str | Path,
        file_path: str,
        revision: str = "HEAD",
    ) -> bytes | None:
        """Return the content of a tracked file at a given revision."""
        with self._open_repository(repository_path) as repo:
            try:
                commit_id = parse_commit(repo, revision).id
            except (KeyError, ValueError) as e:
                error_msg = f"Unknown revision '{revision}' in {repository_path}"
                raise VersionerError(error_msg) from e

            try:
                _, blob_id = tree_lookup_path(
                    repo.get_object,
                    repo[commit_id].tree,
                    file_path.encode(),
                )
            except KeyError:
                return None

            return cast("Blob", repo[blob_id]).data

    @override
    def remote_url(self, repository_path: str | Path, remote: str = "origin") -> str:
        """Return the configured URL of a remote."""
        with self._open_repository(repository_path) as repo:
            config = repo.get_config()
            try:
                url = config.get((b"remote", remote.encode()), b"url")
            except KeyError as e:
                error_msg = f"No '{remote}' remote configured in {repository_path}"
                raise RemoteNotFoundError(error_msg) from e
            return url.decode() if isinstance(url, bytes) else str(url)

    @override
    def status(self, repository_path: str | Path) -> RepoStatus:
        """Return the staged, unstaged and untracked paths of the repository."""
        with self._open_repository(repository_path) as repo:
            try:
                raw = porcelain.status(repo)
            except _DULWICH_ERRORS as e:
                error_msg = f"Failed to read repository status: {e}"
                raise VersionerError(error_msg) from e

            staged = raw.staged or {}
            return RepoStatus(
                staged_added=self._decode_paths(staged.get("add")),
                staged_deleted=self._decode_paths(staged.get("delete")),
                staged_modified=self._decode_paths(staged.get("modify")),
                unstaged=self._decode_paths(raw.unstaged),
                untracked=self._decode_paths(raw.untracked),
            )

    @override
    def is_bare(self, repository_path: str | Path) -> bool:
        """Return whether the repository is bare."""
        with self._open_repository(repository_path) as repo:
            return bool(repo.bare)

    @override
    def working_dir(self, repository_path: str | Path) -> str:
        """Return the absolute path of the repository working tree."""
        with self._open_repository(repository_path) as repo:
            if repo.bare:
                error_msg = f"Bare repository has no working tree: {repository_path}"
                raise VersionerError(error_msg)
            return str(Path(repo.path).resolve())

    @override
    def list_local_branches(self, repository_path: str | Path) -> list[str]:
        """List local branch names present in the repository."""
        with self._open_repository(repository_path) as repo:
            branches = [
                ref[len(_LOCAL_BRANCH_PREFIX) :].decode()
                for ref in repo.get_refs()
                if ref.startswith(_LOCAL_BRANCH_PREFIX)
            ]
        return sorted(set(branches))

    @override
    def ahead_behind(
        self, repository_path: str | Path, branch: str | None = None
    ) -> tuple[int, int]:
        """Count commits the local branch is ahead of and behind its remote."""
        with self._open_repository(repository_path) as repo:
            branch_name = branch or self._get_current_branch_name(repo)
            refs = repo.get_refs()

            local_sha = refs.get(_LOCAL_BRANCH_PREFIX + branch_name.encode())
            if local_sha is None:
                error_msg = f"Local branch '{branch_name}' not found"
                raise BranchNotFoundError(error_msg)

            remote_sha = refs.get(_REMOTE_BRANCH_PREFIX + branch_name.encode())
            if remote_sha is None or remote_sha == local_sha:
                # No remote-tracking branch, or already in sync.
                return (0, 0)

            try:
                bases = find_merge_base(repo, [local_sha, remote_sha])
            except _DULWICH_ERRORS as e:
                error_msg = f"Failed to compare '{branch_name}' with its remote: {e}"
                raise VersionerError(error_msg) from e

            ahead = self._count_commits(repo, local_sha, bases)
            behind = self._count_commits(repo, remote_sha, bases)
            return (ahead, behind)

    @staticmethod
    def _count_commits(repo: Repo, tip: bytes, exclude: list[bytes]) -> int:
        """Count commits reachable from ``tip`` but not from ``exclude``."""
        return sum(1 for _ in repo.get_walker(include=[tip], exclude=list(exclude)))

    @override
    def add(
        self,
        repository_path: str | Path,
        files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area using Dulwich.

        ``porcelain.add(paths=".")`` also stages deletions, so passing None is
        equivalent to ``git add --all``.

        Args:
            repository_path: Path to the local repository.
            files: List of files to add. If None, adds all changes.

        Raises:
            VersionerError: If the add operation fails.

        """
        try:
            with self._open_repository(repository_path) as repo:
                if files is None:
                    porcelain.add(repo, paths=".")
                else:
                    porcelain.add(repo, paths=files)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to add files to repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def remove(self, repository_path: str | Path, files: list[str]) -> None:
        """Remove files from the index and the working tree using Dulwich."""
        if not files:
            return

        try:
            with self._open_repository(repository_path) as repo:
                porcelain.remove(repo, paths=list(files))
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to remove files from repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def unstage(self, repository_path: str | Path, files: list[str]) -> None:
        """Reset the index entries of ``files`` to HEAD, keeping the working tree."""
        if not files:
            return

        try:
            with self._open_repository(repository_path) as repo:
                porcelain.restore(
                    repo,
                    paths=cast("list[bytes | str]", list(files)),
                    staged=True,
                    worktree=False,
                )
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to unstage files: {e}"
            raise VersionerError(error_msg) from e

    @override
    def restore_files(self, repository_path: str | Path, files: list[str]) -> None:
        """Restore working tree files from the index, discarding local edits."""
        if not files:
            return

        try:
            with self._open_repository(repository_path) as repo:
                porcelain.restore(
                    repo,
                    paths=cast("list[bytes | str]", list(files)),
                    staged=False,
                    worktree=True,
                )
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to restore files: {e}"
            raise VersionerError(error_msg) from e

    @override
    def reset_hard(self, repository_path: str | Path, treeish: str = "HEAD") -> None:
        """Reset HEAD, index and working tree to ``treeish`` using Dulwich."""
        try:
            with self._open_repository(repository_path) as repo:
                porcelain.reset(repo, "hard", treeish)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to reset repository to '{treeish}': {e}"
            raise VersionerError(error_msg) from e
        except KeyError as e:
            error_msg = f"Cannot reset to unknown revision '{treeish}'"
            raise VersionerError(error_msg) from e

    @override
    def create_tag(
        self,
        repository_path: str | Path,
        tag_name: str,
        message: str | None = None,
    ) -> None:
        """Create a lightweight or annotated tag at HEAD using Dulwich."""
        try:
            with self._open_repository(repository_path) as repo:
                if tag_name.encode() in porcelain.tag_list(repo):
                    error_msg = f"Tag '{tag_name}' already exists"
                    raise VersionerError(error_msg)

                if message is None:
                    porcelain.tag_create(repo, tag_name)
                else:
                    porcelain.tag_create(
                        repo,
                        tag_name,
                        author=self._author.to_bytes(),
                        message=message.encode(),
                        annotated=True,
                    )
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to create tag '{tag_name}': {e}"
            raise VersionerError(error_msg) from e

    @override
    def list_tags(self, repository_path: str | Path) -> list[str]:
        """List tag names present in the repository."""
        with self._open_repository(repository_path) as repo:
            tags = [
                tag.decode() if isinstance(tag, bytes) else tag
                for tag in porcelain.tag_list(repo)
            ]
        return sorted(tags)

    @override
    def fetch(self, repository_path: str | Path) -> None:
        """Fetch latest changes from the remote repository using Dulwich.

        Args:
            repository_path: Path to the local repository.

        Raises:
            VersionerError: If the fetch operation fails.

        """
        try:
            with self._open_repository(repository_path) as repo:
                remote_kwargs = self._dulwich_remote_kwargs()

                try:
                    # errstream swallows the transfer progress dulwich would
                    # otherwise print on stdout, in the middle of a report.
                    porcelain.fetch(repo, b"origin", errstream=BytesIO(), **remote_kwargs)
                except KeyError as e:
                    error_msg = "No 'origin' remote found in repository"
                    raise RemoteNotFoundError(error_msg) from e

        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to fetch from remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to fetch from remote repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def pull(self, repository_path: str | Path, branch: str) -> PullResult:
        """Pull latest changes from the remote repository using Dulwich.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Returns:
            The paths added, modified and deleted by the pull.

        Raises:
            VersionerError: If the pull operation fails.

        """
        try:
            with self._open_repository(repository_path) as repo:
                remote_kwargs = self._dulwich_remote_kwargs()
                remote_branch_ref = _REMOTE_BRANCH_PREFIX + branch.encode()

                try:
                    # errstream swallows the transfer progress dulwich would
                    # otherwise print on stdout, in the middle of a report.
                    porcelain.fetch(repo, b"origin", errstream=BytesIO(), **remote_kwargs)
                except KeyError as e:
                    error_msg = "No 'origin' remote found in repository"
                    raise RemoteNotFoundError(error_msg) from e

                self._ensure_remote_branch_exists(repo, remote_branch_ref, branch)

                self._get_current_branch_name(repo)
                old_commit = self._head_sha(repo)
                # merge reports conflicts instead of raising, and leaves the
                # working tree conflicted: surface them rather than returning
                # what would look like an empty pull.
                _, conflicts = porcelain.merge(repo, f"origin/{branch}")
                self._raise_on_merge_conflicts(branch, conflicts)
                new_commit = self._head_sha(repo)

                return self._build_pull_result(repo, old_commit, new_commit)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to pull from remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to pull from remote repository: {e}"
            raise VersionerError(error_msg) from e

    @classmethod
    def _raise_on_merge_conflicts(cls, branch: str, conflicts: list[bytes]) -> None:
        """Raise when a merge left conflicted paths in the working tree.

        Args:
            branch: Remote branch that was merged, used in the message.
            conflicts: Conflicted paths as reported by dulwich.

        Raises:
            MergeConflictError: If ``conflicts`` is not empty.

        """
        if not conflicts:
            return

        conflicted = cls._decode_paths(conflicts)
        error_msg = (
            f"Pulling 'origin/{branch}' left {len(conflicted)} conflicted "
            f"file(s) to resolve manually: {', '.join(conflicted)}"
        )
        raise MergeConflictError(error_msg, conflicted)

    @staticmethod
    def _head_sha(repo: Repo) -> bytes | None:
        """Return the commit id HEAD points to, or None on an unborn branch."""
        try:
            return repo.head()
        except KeyError:
            return None

    @classmethod
    def _build_pull_result(
        cls,
        repo: Repo,
        old_commit: bytes | None,
        new_commit: bytes | None,
    ) -> PullResult:
        """Diff two commits into a :class:`PullResult`.

        Args:
            repo: Open repository owning both commits.
            old_commit: Commit id before the pull, or None on an unborn branch.
            new_commit: Commit id after the pull, or None on an unborn branch.

        Returns:
            The structured list of added, modified and deleted paths.

        """
        result = PullResult(
            old_commit_id=old_commit.decode() if old_commit else None,
            new_commit_id=new_commit.decode() if new_commit else None,
        )
        if old_commit == new_commit or new_commit is None:
            return result

        old_tree = repo[old_commit].tree if old_commit else None
        new_tree = repo[new_commit].tree

        for change in tree_changes(repo.object_store, old_tree, new_tree):
            if change.type == CHANGE_ADD:
                result.added.append(change.new.path.decode())
            elif change.type == CHANGE_DELETE:
                result.deleted.append(change.old.path.decode())
            elif change.type == CHANGE_MODIFY:
                result.modified.append(change.new.path.decode())

        result.added.sort()
        result.modified.sort()
        result.deleted.sort()
        return result

    def _ensure_remote_branch_exists(
        self, repo: Repo, remote_branch_ref: bytes, branch: str
    ) -> None:
        """Raise if a remote-tracking branch ref is missing from the repository.

        Args:
            repo: Repository whose refs should be checked.
            remote_branch_ref: Fully-qualified remote-tracking ref
                (e.g. ``b"refs/remotes/origin/main"``).
            branch: Branch name, used for the error message.

        Raises:
            BranchNotFoundError: If the ref is not present among the repository's refs.

        """
        refs = repo.get_refs()
        if remote_branch_ref not in refs:
            error_msg = f"Remote branch 'origin/{branch}' not found"
            raise BranchNotFoundError(error_msg)

    @override
    def commit(
        self,
        repository_path: str | Path,
        message: str,
        author: Author | None = None,
    ) -> str | None:
        """Commit staged changes using Dulwich.

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
        try:
            with self._open_repository(repository_path) as repo:
                if not self._has_staged_changes(repo):
                    return None

                author_bytes = (author or self._author).to_bytes()
                commit_id = porcelain.commit(
                    repo,
                    message=message,
                    author=author_bytes,
                    committer=author_bytes,
                )
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to commit changes: {e}"
            raise VersionerError(error_msg) from e

        return commit_id.decode() if isinstance(commit_id, bytes) else str(commit_id)

    @override
    def push(self, repository_path: str | Path, branch: str) -> None:
        """Push commits to the remote repository using Dulwich.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to push to.

        Raises:
            VersionerError: If the push operation fails.

        """
        try:
            with self._open_repository(repository_path) as repo:
                current_branch = self._get_current_branch_name(repo)
                remote_kwargs = self._dulwich_remote_kwargs()
                refspec = f"refs/heads/{current_branch}:refs/heads/{branch}"
                porcelain.push(
                    repo, b"origin", refspecs=[refspec], errstream=BytesIO(), **remote_kwargs
                )
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to push to remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to push to remote repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def push_branches(self, repository_path: str | Path, branches: list[str]) -> None:
        """Push multiple branches to the remote in a single operation using Dulwich.

        Args:
            repository_path: Path to the local repository.
            branches: Local branch names to push to same-named remote branches.

        Raises:
            VersionerError: If the push operation fails.

        """
        if not branches:
            return

        try:
            with self._open_repository(repository_path) as repo:
                remote_kwargs = self._dulwich_remote_kwargs()
                refspecs = [
                    f"refs/heads/{branch}:refs/heads/{branch}" for branch in branches
                ]
                porcelain.push(
                    repo, b"origin", refspecs=refspecs, errstream=BytesIO(), **remote_kwargs
                )
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to push branches to remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to push branches to remote repository: {e}"
            raise VersionerError(error_msg) from e

    def _ensure_clean_clone_target(self, target_path: Path) -> None:
        """Remove an existing clone target directory and verify the cleanup.

        Args:
            target_path: Local path where the repository should be cloned.

        Raises:
            VersionerError: If the directory still exists after removal.

        """
        if target_path.exists():
            shutil.rmtree(target_path)

        if target_path.exists():
            error_msg = f"Target directory still exists after cleanup: {target_path}"
            raise VersionerError(error_msg)

    @override
    def clone(
        self,
        repository_url: str,
        target_path: str | Path,
        *,
        branch: str | None = None,
        depth: int | None = None,
    ) -> Repo:
        """Clone a repository using Dulwich.

        The remote's ``fetch`` refspec (``+refs/heads/*:refs/remotes/origin/*``)
        is applied regardless of ``branch``, so every remote branch is fetched
        into a local remote-tracking ref; ``branch`` only selects which one is
        checked out as HEAD. This means a caller can later use :meth:`checkout`
        to switch to any other remote branch without cloning again.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Optional branch to check out as HEAD after cloning. If
                None, the repository's default branch is checked out.
            depth: Optional shallow clone depth.

        Returns:
            Repo: The freshly cloned Dulwich repository, so callers (e.g.
            :class:`~git.provider.provider_mixin.ProviderMixin`) can cache it
            and avoid re-cloning when trying alternate branches.

        Raises:
            VersionerError: If the clone operation fails.

        """
        try:
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            self._ensure_clean_clone_target(target_path)

            remote_kwargs = self._dulwich_remote_kwargs()
            clone_kwargs = dict(remote_kwargs)
            if branch is not None:
                clone_kwargs["branch"] = branch
            if depth is not None:
                clone_kwargs["depth"] = depth
            return porcelain.clone(repository_url, str(target_path), errstream=BytesIO(), **clone_kwargs)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to clone repository from {repository_url}: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to clone repository from {repository_url}: {e}"
            raise VersionerError(error_msg) from e

    @override
    def list_remote_branches(self, repository_url: str) -> list[str]:
        """List branch names available on the remote repository.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            Sorted unique branch names reported by ``ls-remote``.

        Raises:
            VersionerError: If the remote cannot be queried.

        """
        try:
            remote_kwargs = self._dulwich_remote_kwargs()
            refs = porcelain.ls_remote(repository_url, **remote_kwargs)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to list remote branches for {repository_url}: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to list remote branches for {repository_url}: {e}"
            raise VersionerError(error_msg) from e

        branches: list[str] = []
        for ref in refs:
            ref_bytes = ref if isinstance(ref, bytes) else ref.encode()
            if ref_bytes.startswith(_LOCAL_BRANCH_PREFIX):
                branches.append(ref_bytes[len(_LOCAL_BRANCH_PREFIX) :].decode())
        return sorted(set(branches))

    def _get_available_branches(self, repo: Repo) -> list[str]:
        """Get all available branches (local and remote) from repository.

        Args:
            repo: Dulwich repository object.

        Returns:
            List of available branch names.

        """
        available_branches: list[str] = []
        for ref in repo.get_refs():
            if ref.startswith(_LOCAL_BRANCH_PREFIX):
                available_branches.append(ref[len(_LOCAL_BRANCH_PREFIX) :].decode())
            elif ref.startswith(_REMOTE_BRANCH_PREFIX):
                available_branches.append(ref[len(_REMOTE_BRANCH_PREFIX) :].decode())
        return available_branches

    def _create_branch_not_found_error(
        self, branch: str, available_branches: list[str]
    ) -> VersionerError:
        """Create a branch not found error with available branches.

        Args:
            branch: The requested branch name.
            available_branches: List of available branches.

        Returns:
            BranchNotFoundError with informative message.

        """
        if available_branches:
            error_msg = f"Version '{branch}' not found. Available versions: {', '.join(available_branches)}"
        else:
            error_msg = f"Version '{branch}' not found"
        return BranchNotFoundError(error_msg)

    def _checkout_remote_branch(self, repo: Repo, branch: str) -> None:
        """Checkout a remote branch by creating a local tracking branch.

        Args:
            repo: Dulwich repository object.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """
        try:
            porcelain.branch_create(repo, branch, objectish=f"origin/{branch}")
            porcelain.checkout(repo, target=branch)
        except _DULWICH_ERRORS as e:
            error_msg = (
                f"Failed to create and checkout branch '{branch}' from remote: {e}"
            )
            raise VersionerError(error_msg) from e

    def _checkout_local_branch(self, repo: Repo, branch: str) -> None:
        """Checkout an existing local branch.

        Args:
            repo: Dulwich repository object.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """
        try:
            porcelain.checkout(repo, target=branch)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to checkout local branch '{branch}': {e}"
            raise VersionerError(error_msg) from e

    @override
    def checkout(self, repository_path: str | Path, branch: str) -> None:
        """Checkout a specific branch in the repository using Dulwich.

        Args:
            repository_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """
        try:
            with self._open_repository(repository_path) as repo:
                refs = repo.get_refs()
                local_ref = _LOCAL_BRANCH_PREFIX + branch.encode()
                remote_ref = _REMOTE_BRANCH_PREFIX + branch.encode()

                if local_ref in refs:
                    self._checkout_local_branch(repo, branch)
                elif remote_ref in refs:
                    self._checkout_remote_branch(repo, branch)
                else:
                    available_branches = self._get_available_branches(repo)
                    raise self._create_branch_not_found_error(
                        branch, available_branches
                    )
        except VersionerError:
            raise
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to checkout branch '{branch}': {e}"
            raise VersionerError(error_msg) from e

    @override
    def select_branch(
        self, repository_path: str | Path, branches: list[str]
    ) -> str | None:
        """Select the first available branch from a list of branches.

        This method checks for the existence of each branch in the provided list
        without performing any checkout operations. It returns the first branch
        that exists locally or remotely.

        Args:
            repository_path: Path to the local repository.
            branches: List of branch names to try in order.

        Returns:
            str | None: The name of the first available branch,
                or None if no branch could be found.

        Raises:
            VersionerError: If there's an error with the repository or versioner.

        """
        if not branches:
            return None

        with self._open_repository(repository_path) as repo:
            refs = repo.get_refs()

            for branch in branches:
                local_ref = _LOCAL_BRANCH_PREFIX + branch.encode()
                if local_ref in refs:
                    return branch

                remote_ref = _REMOTE_BRANCH_PREFIX + branch.encode()
                if remote_ref in refs:
                    return branch

        return None

    @override
    def stash(self, repository_path: str | Path, message: str | None = None) -> bool:
        """Stash current changes in the repository using Dulwich.

        Args:
            repository_path: Path to the local repository.
            message: Optional stash message (ignored; Dulwich does not support it).

        Returns:
            bool: True if changes were stashed, False if no changes to stash.

        Raises:
            VersionerError: If the stash operation fails.

        """
        _ = message
        try:
            with self._open_repository(repository_path) as repo:
                if not self._has_working_tree_changes(repo):
                    return False

                porcelain.stash_push(repo)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to stash changes: {e}"
            raise VersionerError(error_msg) from e

        return True

    @override
    def safe_pull(self, repository_path: str | Path, branch: str) -> PullResult:
        """Safely pull latest changes, stashing any local changes first using Dulwich.

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
        try:
            had_stash = self.stash(repository_path, "Safe pull stash")

            try:
                result = self.pull(repository_path, branch)
            except Exception:
                if had_stash:
                    try:
                        self._apply_stash_at(repository_path)
                    except Exception as restore_error:
                        log.warning(
                            "Failed to restore stash after pull failure: %s",
                            restore_error,
                        )
                raise

            if had_stash:
                self._apply_stash_at(repository_path)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to perform safe pull: {e}"
            raise VersionerError(error_msg) from e

        return result

    def _apply_stash_at(self, repository_path: str | Path) -> None:
        """Apply the most recent stash of the repository at the given path.

        Args:
            repository_path: Path to the local repository.

        Raises:
            VersionerError: If the stash apply operation fails.

        """
        with self._open_repository(repository_path) as repo:
            self._apply_stash(repo)

    def _apply_stash(self, repo: Repo) -> None:
        """Apply the most recent stash to the repository.

        Args:
            repo: Dulwich repository object.

        Raises:
            VersionerError: If the stash apply operation fails.

        """
        try:
            if not list(porcelain.stash_list(repo)):
                return
            porcelain.stash_pop(repo)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to apply stash: {e}"
            raise VersionerError(error_msg) from e

    @override
    def remote_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using ls-remote.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            remote_kwargs = self._dulwich_remote_kwargs()
            porcelain.ls_remote(repository_url, **remote_kwargs)
        except Exception:
            log.debug("Repository does not exist or is not accessible")
            return False
        return True
