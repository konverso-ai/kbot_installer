"""Dulwich versioner for full git operations.

This module implements the DulwichVersioner class that handles full git
operations using Dulwich for any git repository.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, cast

from auth.base import HttpAuthBase, RemoteKwargs
from dulwich import porcelain
from dulwich.errors import GitProtocolError, HangupException, NotGitRepository
from dulwich.porcelain import Error as DulwichPorcelainError
from dulwich.refs import Ref
from dulwich.repo import Repo
from typing_extensions import override

from git.versioner.author import Author
from git.versioner.base import VersionerError
from git.versioner.str_repr_mixin import StrReprMixin

logger = logging.getLogger(__name__)

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
        auth (HttpAuthBase | None): Authentication object for git operations.
        author (Author): Author identity used for commit metadata.

    """

    def __init__(
        self,
        auth: HttpAuthBase | None = None,
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
    def _get_auth(self) -> HttpAuthBase | None:
        """Get the authentication object for git operations.

        Returns:
            HttpAuthBase | None: The authentication object or None.

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
        return cast(dict[str, Any], self._get_remote_kwargs())

    def _get_repository(self, repository_path: str | Path) -> Repo:
        """Get a Dulwich Repo object from the given path.

        Args:
            repository_path: Path to the local repository.

        Returns:
            Repo: Repository object.

        Raises:
            VersionerError: If the repository cannot be opened.

        """
        repo_path = Path(repository_path)
        if not repo_path.exists():
            error_msg = f"Repository path does not exist: {repo_path}"
            raise VersionerError(error_msg)

        try:
            return Repo(str(repo_path))
        except NotGitRepository as e:
            error_msg = f"Failed to open repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e

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
        return bool(
            staged.get("add") or staged.get("delete") or staged.get("modify")
        )

    def _get_current_branch_name(self, repo: Repo) -> str:
        """Return the current branch name from HEAD.

        Raises:
            VersionerError: If HEAD does not point to a local branch.

        """
        _, branch_ref = repo.refs.follow(cast(Ref, b"HEAD"))
        if branch_ref is None or not branch_ref.startswith(_LOCAL_BRANCH_PREFIX):
            error_msg = "No current branch found"
            raise VersionerError(error_msg)
        return branch_ref[len(_LOCAL_BRANCH_PREFIX) :].decode()

    @override
    def add(
        self,
        repository_path: str | Path,
        files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area using Dulwich.

        Args:
            repository_path: Path to the local repository.
            files: List of files to add. If None, adds all changes.

        Raises:
            VersionerError: If the add operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            if files is None:
                porcelain.add(repo, paths=".")
            else:
                porcelain.add(repo, paths=files)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to add files to repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def fetch(self, repository_path: str | Path, branch: str) -> None:
        """Fetch latest changes from the remote repository using Dulwich.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to fetch from.

        Raises:
            VersionerError: If the fetch operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            remote_kwargs = self._dulwich_remote_kwargs()

            try:
                porcelain.fetch(repo, b"origin", **remote_kwargs)
            except KeyError as e:
                error_msg = "No 'origin' remote found in repository"
                raise VersionerError(error_msg) from e

        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to fetch from remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to fetch from remote repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def pull(self, repository_path: str | Path, branch: str) -> None:
        """Pull latest changes from the remote repository using Dulwich.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Raises:
            VersionerError: If the pull operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            remote_kwargs = self._dulwich_remote_kwargs()
            remote_branch_ref = _REMOTE_BRANCH_PREFIX + branch.encode()

            try:
                porcelain.fetch(repo, b"origin", **remote_kwargs)
            except KeyError as e:
                error_msg = "No 'origin' remote found in repository"
                raise VersionerError(error_msg) from e

            refs = repo.get_refs()
            if remote_branch_ref not in refs:
                error_msg = f"Remote branch 'origin/{branch}' not found"
                raise VersionerError(error_msg)

            self._get_current_branch_name(repo)
            porcelain.merge(repo, f"origin/{branch}")
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to pull from remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to pull from remote repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def commit(self, repository_path: str | Path, message: str) -> None:
        """Commit staged changes using Dulwich.

        Args:
            repository_path: Path to the local repository.
            message: Commit message.

        Raises:
            VersionerError: If the commit operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            if not self._has_staged_changes(repo):
                return

            author_bytes = self._author.to_bytes()
            porcelain.commit(
                repo,
                message=message,
                author=author_bytes,
                committer=author_bytes,
            )
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to commit changes: {e}"
            raise VersionerError(error_msg) from e

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
            repo = self._get_repository(repository_path)
            current_branch = self._get_current_branch_name(repo)
            remote_kwargs = self._dulwich_remote_kwargs()
            refspec = f"refs/heads/{current_branch}:refs/heads/{branch}"
            porcelain.push(repo, b"origin", refspecs=[refspec], **remote_kwargs)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to push to remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to push to remote repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def push_branches(
        self, repository_path: str | Path, branches: list[str]
    ) -> None:
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
            repo = self._get_repository(repository_path)
            remote_kwargs = self._dulwich_remote_kwargs()
            refspecs = [
                f"refs/heads/{branch}:refs/heads/{branch}" for branch in branches
            ]
            porcelain.push(repo, b"origin", refspecs=refspecs, **remote_kwargs)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to push branches to remote repository: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to push branches to remote repository: {e}"
            raise VersionerError(error_msg) from e

    @override
    def clone(
        self,
        repository_url: str,
        target_path: str | Path,
        *,
        branch: str | None = None,
        depth: int | None = None,
    ) -> None:
        """Clone a repository using Dulwich.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.
            branch: Optional branch to clone and check out.
            depth: Optional shallow clone depth.

        Raises:
            VersionerError: If the clone operation fails.

        """
        try:
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if target_path.exists():
                shutil.rmtree(target_path)

            if target_path.exists():
                error_msg = (
                    f"Target directory still exists after cleanup: {target_path}"
                )
                raise VersionerError(error_msg)

            remote_kwargs = self._dulwich_remote_kwargs()
            clone_kwargs = dict(remote_kwargs)
            if branch is not None:
                clone_kwargs["branch"] = branch
            if depth is not None:
                clone_kwargs["depth"] = depth
            porcelain.clone(repository_url, str(target_path), **clone_kwargs)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to clone repository from {repository_url}: {e}"
            raise VersionerError(error_msg) from e
        except VersionerError:
            raise
        except Exception as e:
            error_msg = f"Failed to clone repository from {repository_url}: {e}"
            raise VersionerError(error_msg) from e

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
            error_msg = (
                f"Failed to list remote branches for {repository_url}: {e}"
            )
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Failed to list remote branches for {repository_url}: {e}"
            )
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
            VersionerError with informative message.

        """
        if available_branches:
            error_msg = f"Version '{branch}' not found. Available versions: {', '.join(available_branches)}"
        else:
            error_msg = f"Version '{branch}' not found"
        return VersionerError(error_msg)

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
            repo = self._get_repository(repository_path)
            refs = repo.get_refs()
            local_ref = _LOCAL_BRANCH_PREFIX + branch.encode()
            remote_ref = _REMOTE_BRANCH_PREFIX + branch.encode()

            if remote_ref in refs:
                self._checkout_remote_branch(repo, branch)
            elif local_ref in refs:
                self._checkout_local_branch(repo, branch)
            else:
                available_branches = self._get_available_branches(repo)
                raise self._create_branch_not_found_error(branch, available_branches)
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

        repo = self._get_repository(repository_path)
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
            repo = self._get_repository(repository_path)
            if not self._has_working_tree_changes(repo):
                return False

            porcelain.stash_push(repo)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to stash changes: {e}"
            raise VersionerError(error_msg) from e

        return True

    @override
    def safe_pull(self, repository_path: str | Path, branch: str) -> None:
        """Safely pull latest changes, stashing any local changes first using Dulwich.

        This method performs a safe pull by:
        1. Stashing any local changes
        2. Pulling the latest changes from remote
        3. Applying the stashed changes back

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Raises:
            VersionerError: If the safe pull operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            had_stash = self.stash(repository_path, "Safe pull stash")

            try:
                self.pull(repository_path, branch)
            except Exception:
                if had_stash:
                    try:
                        self._apply_stash(repo)
                    except Exception as restore_error:
                        logger.warning(
                            "Failed to restore stash after pull failure: %s",
                            restore_error,
                        )
                raise

            if had_stash:
                self._apply_stash(repo)
        except _DULWICH_ERRORS as e:
            error_msg = f"Failed to perform safe pull: {e}"
            raise VersionerError(error_msg) from e

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
            logger.debug("Repository does not exist or is not accessible")
            return False
        else:
            return True
