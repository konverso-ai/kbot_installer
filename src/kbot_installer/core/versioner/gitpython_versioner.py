"""GitPython implementation of the versioner.

This module provides a concrete implementation of VersionerBase using GitPython
for all git operations including clone, checkout, add, pull, commit, and push.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

import git
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)
from kbot_installer.core.versioner.str_repr_mixin import StrReprMixin
from kbot_installer.core.versioner.versioner_base import VersionerError

logger = logging.getLogger(__name__)


class GitPythonVersioner(StrReprMixin):
    """GitPython implementation of the versioner.

    This class provides a concrete implementation of VersionerBase using GitPython
    for all git operations. It supports authentication and handles all git commands
    asynchronously.

    Attributes:
        name (str): Name of the versioner ("gitpython").
        base_url (str): Base URL of the versioner (empty for GitPython).
        auth (PyGitAuthenticationBase | None): Authentication object for git operations.

    """

    def __init__(self, auth: PyGitAuthenticationBase | None = None) -> None:
        """Initialize the GitPython versioner.

        Args:
            auth (PyGitAuthenticationBase | None, optional): Authentication object.
                Defaults to None.

        """
        self.name = "gitpython"
        self.base_url = ""
        self._auth = auth

    def _get_auth(self) -> PyGitAuthenticationBase | None:
        """Get the authentication object for git operations.

        Returns:
            PyGitAuthenticationBase | None: The authentication object or None.

        """
        return self._auth

    async def clone(self, repository_url: str, target_path: str | Path) -> None:
        """Clone a repository to the specified path.

        Args:
            repository_url: URL of the repository to clone.
            target_path: Local path where the repository should be cloned.

        Raises:
            VersionerError: If the clone operation fails.

        """
        try:
            target_path = Path(target_path)

            # Prepare clone options
            clone_options: dict[str, Any] = {}

            # Add authentication if available
            if self._auth:
                clone_options["env"] = self._auth.get_git_env()

            # Run clone in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Repo.clone_from(repository_url, target_path, **clone_options),
            )

        except GitCommandError as e:
            error_msg = f"Failed to clone repository {repository_url}: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during clone: {e}"
            raise VersionerError(error_msg) from e

    def _get_available_branches(self, repo: Repo) -> list[str]:
        """Get all available branches (local and remote).

        Args:
            repo: Git repository object.

        Returns:
            List of available branch names.

        """
        try:
            # Get all remote branches
            remote_branches = [
                ref.name.replace("origin/", "")
                for ref in repo.remote().refs
                if ref.name.startswith("origin/")
            ]

            # Get all local branches
            local_branches = [ref.name for ref in repo.branches]
            return list(set(remote_branches + local_branches))
        except Exception:
            return []

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

    async def _checkout_local_branch(self, repo: Repo, branch: str) -> None:
        """Checkout an existing local branch.

        Args:
            repo: Git repository object.
            branch: Branch name to checkout.

        """
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: repo.git.checkout(branch)
        )

    async def _checkout_remote_branch(self, repo: Repo, branch: str) -> None:
        """Checkout a remote branch by creating a local tracking branch.

        Args:
            repo: Git repository object.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the remote branch doesn't exist.

        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: repo.git.checkout("-b", branch, f"origin/{branch}"),
            )
        except GitCommandError:
            # Remote branch doesn't exist, get available branches for better error message
            available_branches = self._get_available_branches(repo)
            raise self._create_branch_not_found_error(
                branch, available_branches
            ) from None

    async def checkout(self, repository_path: str | Path, branch: str) -> None:
        """Checkout a specific branch in the repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch name to checkout.

        Raises:
            VersionerError: If the checkout operation fails.

        """
        try:
            repository_path = Path(repository_path)
            repo = Repo(repository_path)

            # Check if branch exists locally
            if branch in [ref.name for ref in repo.branches]:
                await self._checkout_local_branch(repo, branch)
            else:
                await self._checkout_remote_branch(repo, branch)

        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e
        except GitCommandError as e:
            error_msg = f"Failed to checkout branch {branch}: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during checkout: {e}"
            raise VersionerError(error_msg) from e

    async def select_branch(
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
        try:
            for branch in branches:
                try:
                    await self.checkout(repository_path, branch)
                except VersionerError:
                    # Continue to next branch if this one fails
                    continue
                else:
                    return branch

        except Exception as e:
            error_msg = f"Unexpected error during branch selection: {e}"
            raise VersionerError(error_msg) from e

        return None

    async def add(
        self,
        repository_path: str | Path,
        files: list[str] | None = None,
    ) -> None:
        """Add files to the staging area.

        Args:
            repository_path: Path to the local repository.
            files: List of files to add. If None, adds all changes.

        Raises:
            VersionerError: If the add operation fails.

        """
        try:
            repository_path = Path(repository_path)
            repo = Repo(repository_path)

            if files is None:
                # Add all changes
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: repo.git.add(".")
                )
            else:
                # Add specific files
                for file_path in files:
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda f=file_path: repo.git.add(f)
                    )

        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e
        except GitCommandError as e:
            error_msg = f"Failed to add files: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during add: {e}"
            raise VersionerError(error_msg) from e

    async def pull(self, repository_path: str | Path, branch: str) -> None:
        """Pull latest changes from the remote repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to pull from.

        Raises:
            VersionerError: If the pull operation fails.

        """
        try:
            repository_path = Path(repository_path)
            repo = Repo(repository_path)

            # Prepare pull options
            pull_options: dict[str, Any] = {}

            # Add authentication if available
            if self._auth:
                pull_options["env"] = self._auth.get_git_env()

            # Run pull in executor
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: repo.git.pull("origin", branch, **pull_options)
            )

        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e
        except GitCommandError as e:
            error_msg = f"Failed to pull from {branch}: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during pull: {e}"
            raise VersionerError(error_msg) from e

    async def commit(self, repository_path: str | Path, message: str) -> None:
        """Commit staged changes.

        Args:
            repository_path: Path to the local repository.
            message: Commit message.

        Raises:
            VersionerError: If the commit operation fails.

        """
        try:
            repository_path = Path(repository_path)
            repo = Repo(repository_path)

            # Check if there are staged changes
            if not repo.index.diff("HEAD"):
                # No changes to commit
                return

            # Prepare commit options
            commit_options: dict[str, Any] = {"m": message}

            # Add authentication if available
            if self._auth:
                commit_options["env"] = self._auth.get_git_env()

            # Run commit in executor
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: repo.git.commit(**commit_options)
            )

        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e
        except GitCommandError as e:
            error_msg = f"Failed to commit changes: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during commit: {e}"
            raise VersionerError(error_msg) from e

    async def push(self, repository_path: str | Path, branch: str) -> None:
        """Push commits to the remote repository.

        Args:
            repository_path: Path to the local repository.
            branch: Branch to push to.

        Raises:
            VersionerError: If the push operation fails.

        """
        try:
            repository_path = Path(repository_path)
            repo = Repo(repository_path)

            # Prepare push options
            push_options: dict[str, Any] = {}

            # Add authentication if available
            if self._auth:
                push_options["env"] = self._auth.get_git_env()

            # Run push in executor
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: repo.git.push("origin", branch, **push_options)
            )

        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e
        except GitCommandError as e:
            error_msg = f"Failed to push to {branch}: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during push: {e}"
            raise VersionerError(error_msg) from e

    async def stash(
        self, repository_path: str | Path, message: str | None = None
    ) -> bool:
        """Stash current changes in the repository using GitPython.

        Args:
            repository_path: Path to the local repository.
            message: Optional stash message. If None, uses default message.

        Returns:
            bool: True if changes were stashed, False if no changes to stash.

        Raises:
            VersionerError: If the stash operation fails.

        """
        try:
            repository_path = Path(repository_path)
            repo = Repo(repository_path)

            # Check if there are any changes to stash
            if not repo.is_dirty():
                # No changes to stash
                return False

            # Prepare stash options
            stash_message = message or "Auto-stash by versioner"
            stash_options: dict[str, Any] = {"m": stash_message}

            # Add authentication if available
            if self._auth:
                stash_options["env"] = self._auth.get_git_env()

            # Run stash in executor
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: repo.git.stash("push", **stash_options)
            )
            return True  # noqa: TRY300

        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e
        except GitCommandError as e:
            error_msg = f"Failed to stash changes: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during stash: {e}"
            raise VersionerError(error_msg) from e

    async def safe_pull(self, repository_path: str | Path, branch: str) -> None:
        """Safely pull latest changes, stashing any local changes first using GitPython.

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
            repository_path = Path(repository_path)
            repo = Repo(repository_path)

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
                        "Failed to restore stash after pull failure: %s", restore_error
                    )
                raise

            # Step 3: Apply stashed changes back
            await self._apply_stash(repo)

        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid git repository at {repository_path}: {e}"
            raise VersionerError(error_msg) from e
        except GitCommandError as e:
            error_msg = f"Failed to perform safe pull: {e}"
            raise VersionerError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during safe pull: {e}"
            raise VersionerError(error_msg) from e

    async def _apply_stash(self, repo: Repo) -> None:
        """Apply the most recent stash to the repository.

        Args:
            repo: Git repository object.

        Raises:
            VersionerError: If the stash apply operation fails.

        """
        try:
            # Check if there are any stashes
            stash_list = repo.git.stash("list")
            if not stash_list.strip():
                # No stashes to apply, this is normal
                return

            # Apply the most recent stash (stash@{0})
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: repo.git.stash("apply", "stash@{0}")
            )

        except GitCommandError as e:
            error_msg = f"Failed to apply stash: {e}"
            raise VersionerError(error_msg) from e

    async def check_remote_repository_exists(self, repository_url: str) -> bool:
        """Check if a remote repository exists using git ls-remote (most efficient).

        Args:
            repository_url: URL of the remote repository.

        Returns:
            bool: True if repository exists, False otherwise.

        """
        try:
            # Use git ls-remote to check if repository exists
            # This is the most efficient way to check repository existence
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: git.cmd.Git().ls_remote(repository_url)
            )
        except GitCommandError:
            return False
        except Exception:
            return False
        else:
            return True
