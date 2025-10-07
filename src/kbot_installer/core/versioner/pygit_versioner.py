"""PyGit versioner for full git operations.

This module implements the PyGitVersioner class that handles full git
operations using pygit2 for any git repository.
"""

import logging
import shutil
import tempfile
from pathlib import Path

import pygit2

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)
from kbot_installer.core.versioner.str_repr_mixin import StrReprMixin
from kbot_installer.core.versioner.versioner_base import VersionerError

logger = logging.getLogger(__name__)


class PygitVersioner(StrReprMixin):
    """Versioner for git repository operations using pygit2.

    This versioner handles full git operations on any git repository using pygit2
    for git operations. It implements the VersionerBase interface and provides
    all necessary git functionality including clone, add, pull, commit, and push.

    Attributes:
        auth (PyGitAuthenticationBase | None): PyGit authentication object for git operations.

    """

    def __init__(self, auth: PyGitAuthenticationBase | None = None) -> None:
        """Initialize the PyGit versioner.

        Args:
            auth: PyGit authentication object for git operations.
                If None, operations will use public access only.

        """
        self._auth = auth

    def _get_auth(self) -> PyGitAuthenticationBase | None:
        """Get the authentication object for git operations.

        Returns:
            PyGitAuthenticationBase | None: The authentication object or None.

        """
        return self._auth

    def _get_repository(self, repository_path: str | Path) -> pygit2.Repository:
        """Get a pygit2 Repository object from the given path.

        Args:
            repository_path: Path to the local repository.

        Returns:
            pygit2.Repository: Repository object.

        Raises:
            VersionerError: If the repository cannot be opened.

        """
        try:
            repo_path = Path(repository_path)
            if not repo_path.exists():
                error_msg = f"Repository path does not exist: {repo_path}"
                raise VersionerError(error_msg)

            return pygit2.Repository(str(repo_path))
        except pygit2.GitError as e:
            error_msg = f"Failed to open repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e

    async def add(
        self,
        repository_path: str | Path,
        files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area using pygit2.

        Args:
            repository_path: Path to the local repository.
            files: List of files to add. If None, adds all changes.

        Raises:
            VersionerError: If the add operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            index = repo.index

            if files is None:
                # Add all changes
                index.add_all()
            else:
                # Add specific files
                for file_path in files:
                    index.add(file_path)

            index.write()
        except pygit2.GitError as e:
            error_msg = f"Failed to add files to repository: {e}"
            raise VersionerError(error_msg) from e

    async def pull(self, repository_path: str | Path, branch: str) -> None:
        """Pull latest changes from the remote repository using pygit2.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Raises:
            VersionerError: If the pull operation fails.

        """
        try:
            repo = self._get_repository(repository_path)

            # Get the remote (assuming 'origin')
            try:
                remote = repo.remotes["origin"]
            except KeyError as e:
                error_msg = "No 'origin' remote found in repository"
                raise VersionerError(error_msg) from e

            # Fetch the latest changes with authentication if available
            auth = self._get_auth()
            if auth:
                callbacks = auth.get_connector()
                remote.fetch(callbacks=callbacks)
            else:
                remote.fetch()

            # Get the remote branch reference
            remote_branch = f"origin/{branch}"
            try:
                remote_ref = repo.lookup_reference(f"refs/remotes/{remote_branch}")
            except KeyError as e:
                error_msg = f"Remote branch '{remote_branch}' not found"
                raise VersionerError(error_msg) from e

            # Get the current branch
            try:
                _ = repo.head.shorthand  # Check if current branch exists
            except pygit2.GitError as e:
                error_msg = "No current branch found"
                raise VersionerError(error_msg) from e

            # Merge the remote changes
            try:
                repo.merge_analysis(remote_ref.target)
                repo.merge(remote_ref.target)
            except pygit2.GitError as e:
                error_msg = f"Failed to merge remote changes: {e}"
                raise VersionerError(error_msg) from e

        except pygit2.GitError as e:
            error_msg = f"Failed to pull from remote repository: {e}"
            raise VersionerError(error_msg) from e

    async def commit(self, repository_path: str | Path, message: str) -> None:
        """Commit staged changes using pygit2.

        Args:
            repository_path: Path to the local repository.
            message: Commit message.

        Raises:
            VersionerError: If the commit operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            index = repo.index

            # Check if there are any staged changes
            # Compare the current index with the HEAD tree
            try:
                head_tree = repo.head.peel().tree if repo.head.target else None
                current_tree = index.write_tree()

                # If we have a HEAD and the trees are the same, no changes to commit
                if head_tree and current_tree == head_tree:
                    # No staged changes to commit, return without error
                    return
            except pygit2.GitError:
                # No HEAD exists, this will be an initial commit - allow it
                pass

            # Create the commit
            tree = index.write_tree()
            author = pygit2.Signature("Git Versioner", "versioner@example.com")
            committer = author

            # Get parent commit (empty list for initial commit)
            try:
                parent = [repo.head.target] if repo.head.target else []
            except pygit2.GitError:
                parent = []

            repo.create_commit("HEAD", author, committer, message, tree, parent)

        except pygit2.GitError as e:
            error_msg = f"Failed to commit changes: {e}"
            raise VersionerError(error_msg) from e

    async def push(self, repository_path: str | Path, branch: str) -> None:
        """Push commits to the remote repository using pygit2.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to push to.

        Raises:
            VersionerError: If the push operation fails.

        """
        try:
            repo = self._get_repository(repository_path)

            # Get the remote (assuming 'origin')
            try:
                remote = repo.remotes["origin"]
            except KeyError as e:
                error_msg = "No 'origin' remote found in repository"
                raise VersionerError(error_msg) from e

            # Get the current branch
            try:
                current_branch = repo.head.shorthand
            except pygit2.GitError as e:
                error_msg = "No current branch found"
                raise VersionerError(error_msg) from e

            # Push the current branch to the specified remote branch with authentication if available
            auth = self._get_auth()
            if auth:
                callbacks = auth.get_connector()
                remote.push(
                    [f"refs/heads/{current_branch}:refs/heads/{branch}"],
                    callbacks=callbacks,
                )
            else:
                remote.push([f"refs/heads/{current_branch}:refs/heads/{branch}"])

        except pygit2.GitError as e:
            error_msg = f"Failed to push to remote repository: {e}"
            raise VersionerError(error_msg) from e

    async def clone(self, repository_url: str, target_path: str | Path) -> None:
        """Clone a repository using pygit2.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.

        Raises:
            VersionerError: If the clone operation fails.

        """
        try:
            target_path = Path(target_path)

            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove target directory if it exists to avoid conflicts
            if target_path.exists():
                shutil.rmtree(target_path)

            # Verify target directory does not exist
            if target_path.exists():
                error_msg = (
                    f"Target directory still exists after cleanup: {target_path}"
                )
                raise VersionerError(error_msg)

            # Clone the repository with authentication if available
            auth = self._get_auth()
            if auth:
                callbacks = auth.get_connector()
                pygit2.clone_repository(
                    repository_url, str(target_path), callbacks=callbacks
                )
            else:
                pygit2.clone_repository(repository_url, str(target_path))

        except pygit2.GitError as e:
            error_msg = f"Failed to clone repository from {repository_url}: {e}"
            raise VersionerError(error_msg) from e

    def _get_available_branches(self, repo: pygit2.Repository) -> list[str]:
        """Get all available branches (local and remote) from repository.

        Args:
            repo: PyGit2 repository object.

        Returns:
            List of available branch names.

        """
        available_branches = []
        available_refs = list(repo.references)

        for ref in available_refs:
            if ref.startswith("refs/heads/"):
                available_branches.append(ref.replace("refs/heads/", ""))
            elif ref.startswith("refs/remotes/origin/"):
                available_branches.append(ref.replace("refs/remotes/origin/", ""))

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

    def _checkout_remote_branch(self, repo: pygit2.Repository, branch: str) -> None:
        """Checkout a remote branch by creating a local tracking branch.

        Args:
            repo: PyGit2 repository object.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """
        try:
            remote_branch = f"origin/{branch}"
            remote_ref = f"refs/remotes/{remote_branch}"
            local_branch = f"refs/heads/{branch}"
            available_refs = list(repo.references)

            # Check if local branch already exists
            if local_branch in available_refs:
                # Branch exists locally, just checkout
                repo.checkout(local_branch)
            else:
                # Create new branch and checkout
                repo.create_branch(
                    branch,
                    repo.lookup_reference(remote_ref).peel(),
                )
                repo.checkout(local_branch)
        except pygit2.GitError as e:
            error_msg = (
                f"Failed to create and checkout branch '{branch}' from remote: {e}"
            )
            raise VersionerError(error_msg) from e

    def _checkout_local_branch(self, repo: pygit2.Repository, branch: str) -> None:
        """Checkout an existing local branch.

        Args:
            repo: PyGit2 repository object.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """
        try:
            local_branch = f"refs/heads/{branch}"
            repo.checkout(local_branch)
        except pygit2.GitError as e:
            error_msg = f"Failed to checkout local branch '{branch}': {e}"
            raise VersionerError(error_msg) from e

    async def checkout(self, repository_path: str | Path, branch: str) -> None:
        """Checkout a specific branch in the repository using pygit2.

        Args:
            repository_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """
        try:
            repo = self._get_repository(repository_path)
            available_refs = list(repo.references)

            # Check if the branch exists as a remote branch
            remote_branch = f"origin/{branch}"
            remote_ref = f"refs/remotes/{remote_branch}"
            local_branch = f"refs/heads/{branch}"

            if remote_ref in available_refs:
                self._checkout_remote_branch(repo, branch)
            elif local_branch in available_refs:
                self._checkout_local_branch(repo, branch)
            else:
                # Branch doesn't exist, list available branches for better error message
                available_branches = self._get_available_branches(repo)
                raise self._create_branch_not_found_error(branch, available_branches)

        except pygit2.GitError as e:
            error_msg = f"Failed to checkout branch '{branch}': {e}"
            raise VersionerError(error_msg) from e

    async def select_branch(
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

        Example:
            >>> versioner = PygitVersioner()
            >>> branches = ["main", "master", "develop", "dev"]
            >>> selected = await versioner.select_branch("/path/to/repo", branches)
            >>> print(f"Selected branch: {selected}")
            Selected branch: main

        """
        if not branches:
            return None

        repo = self._get_repository(repository_path)
        available_refs = list(repo.references)

        for branch in branches:
            # Check if branch exists locally
            local_ref = f"refs/heads/{branch}"
            if local_ref in available_refs:
                return branch

            # Check if branch exists remotely
            remote_ref = f"refs/remotes/origin/{branch}"
            if remote_ref in available_refs:
                return branch

        # No branch found
        return None

    def _check_remote_repository_exists_with_fetch(self, repository_url: str) -> bool:
        """Check if a remote repository exists using Remote.fetch().

        This method creates a temporary repository and attempts to fetch references
        to determine if the repository exists and is accessible.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        temp_repo_path = None
        try:
            # Create a temporary directory for the repository
            temp_dir = tempfile.mkdtemp()
            temp_repo_path = Path(temp_dir)

            # Initialize a bare repository
            pygit2.init_repository(str(temp_repo_path), bare=True)
            temp_repo = pygit2.Repository(str(temp_repo_path))

            # Add the remote
            remote = temp_repo.remotes.create("temp_remote", repository_url)

            # Try to fetch from the remote with authentication if available
            auth = self._get_auth()
            if auth:
                callbacks = auth.get_connector()
                remote.fetch(callbacks=callbacks)
            else:
                remote.fetch()

        except pygit2.GitError as e:
            logger.debug("Repository does not exist or is not accessible: %s", e)
            return False
        except Exception as e:
            logger.debug("Unexpected error checking repository existence: %s", e)
            return False
        finally:
            # Clean up temporary repository
            if temp_repo_path and temp_repo_path.exists():
                shutil.rmtree(temp_repo_path, ignore_errors=True)

        # If fetch succeeded, the repository exists
        return True

    async def stash(
        self, repository_path: str | Path, message: str | None = None
    ) -> bool:
        """Stash current changes in the repository using pygit2.

        Args:
            repository_path: Path to the local repository.
            message: Optional stash message. If None, uses default message.

        Returns:
            bool: True if changes were stashed, False if no changes to stash.

        Raises:
            VersionerError: If the stash operation fails.

        """
        try:
            repo = self._get_repository(repository_path)

            # Check if there are any changes to stash
            if not repo.status():
                # No changes to stash
                return False

            # Create stash with message
            stash_message = message or "Auto-stash by versioner"
            author = pygit2.Signature("Git Versioner", "versioner@example.com")

            # Create the stash
            repo.stash(author, stash_message)

        except pygit2.GitError as e:
            error_msg = f"Failed to stash changes: {e}"
            raise VersionerError(error_msg) from e

        # Return True after successful stash operation
        return True

    async def safe_pull(self, repository_path: str | Path, branch: str) -> None:
        """Safely pull latest changes, stashing any local changes first using pygit2.

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

            # Step 1: Stash local changes if any exist
            await self.stash(repository_path, "Safe pull stash")

            try:
                # Step 2: Pull latest changes
                await self.pull(repository_path, branch)
            except Exception:
                # If pull fails, try to restore stash
                try:
                    await self._apply_stash(repo)
                except Exception as restore_error:
                    logger.warning(
                        "Failed to restore stash after pull failure: %s",
                        restore_error,
                    )
                raise

            # Step 3: Apply stashed changes back
            await self._apply_stash(repo)

        except pygit2.GitError as e:
            error_msg = f"Failed to perform safe pull: {e}"
            raise VersionerError(error_msg) from e

    async def _apply_stash(self, repo: pygit2.Repository) -> None:
        """Apply the most recent stash to the repository.

        Args:
            repo: PyGit2 repository object.

        Raises:
            VersionerError: If the stash apply operation fails.

        """
        try:
            # Get the most recent stash
            stash_refs = [
                ref for ref in repo.references if ref.startswith("refs/stash")
            ]
            if not stash_refs:
                # No stashes to apply, this is normal
                return

            # Apply the most recent stash (stash@{0})
            repo.stash_apply(0)

        except pygit2.GitError as e:
            error_msg = f"Failed to apply stash: {e}"
            raise VersionerError(error_msg) from e

    async def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using Remote.fetch().

        This method creates a temporary remote and attempts to fetch references
        to determine if the repository exists and is accessible. This is the
        most efficient way to check repository existence with pygit2.

        Args:
            repository_url: URL of the remote repository.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            return self._check_remote_repository_exists_with_fetch(repository_url)
        except Exception:
            logger.exception("Failed to check if remote repository exists")
            return False
