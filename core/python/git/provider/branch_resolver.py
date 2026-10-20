"""Branch-fallback cloning for a single provider.

Given one provider and an ordered list of candidate branches (the requested
branch followed by the provider's configured fallbacks), try to clone using
each branch in turn until one succeeds. This is a "single provider, several
branches" concern, distinct from ``SelectorProvider``'s "several providers"
concern.

The same trial-based fallback applies uniformly to every provider (git-backed
or storage-backed): each candidate branch is attempted through the single
public ``clone_and_checkout`` entry point, falling back to the next candidate
on a "branch not found"-looking failure.
"""

from pathlib import Path

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError


def get_branches_to_try(
    configured_branches: list[str],
    branch: str | None,
) -> list[str]:
    """Get the ordered list of branches to try for a provider.

    Args:
        configured_branches: The provider's own default fallback branches
            (e.g. ``provider.branches``), tried after the requested branch.
        branch: Branch explicitly requested by the caller, or None to use
            the provider's configured branches as-is.

    Returns:
        Branches to try in order: the requested branch first (if any),
        followed by configured fallback branches, without duplicates.

    """
    if not branch:
        return list(configured_branches)
    return list(dict.fromkeys([branch, *configured_branches]))


def _is_branch_not_found_error(error: Exception) -> bool:
    """Return whether an error looks like a missing branch/version."""
    error_str = str(error).lower()
    return "not found" in error_str or "branch" in error_str or "version" in error_str


def _attempt_clone_branch(
    provider: ProviderBase,
    repository_name: str,
    branch: str,
    target_path: Path,
    *,
    commit_id: str | None,
    is_last_branch: bool,
) -> ProviderError | None:
    """Try cloning a single candidate branch.

    Returns:
        None on success, or the retryable ``ProviderError`` encountered.

    Raises:
        ProviderError: If the failure is not retryable with another branch.

    """
    try:
        provider.clone_and_checkout(repository_name, target_path, branch=branch, commit_id=commit_id)
    except ProviderError as e:
        if _is_branch_not_found_error(e) and not is_last_branch:
            return e
        raise
    return None


def clone_with_branch_fallback(
    provider: ProviderBase,
    repository_name: str,
    target_path: Path,
    branches: list[str],
    *,
    commit_id: str | None = None,
) -> str:
    """Clone a repository with a single provider, trying candidate branches.

    Args:
        provider: Provider instance to clone with.
        repository_name: Name of the repository to clone.
        target_path: Local path where the repository should be cloned.
        branches: Candidate branches in priority order. May be empty to use
            the provider's default branch.
        commit_id: Specific commit to pin the checkout to, when supported by
            the provider.

    Returns:
        The branch that was used, or ``""`` if none was requested/needed.

    Raises:
        ProviderError: If every candidate branch fails.

    """
    if not branches:
        provider.clone_and_checkout(repository_name, target_path, commit_id=commit_id)
        return ""

    last_error: ProviderError | None = None
    for branch in branches:
        error = _attempt_clone_branch(
            provider,
            repository_name,
            branch,
            target_path,
            commit_id=commit_id,
            is_last_branch=branch == branches[-1],
        )
        if error is None:
            return branch
        last_error = error

    if last_error:
        raise last_error
    error_msg = f"Failed to download repository with any branch from fallback list: {branches}"
    raise ProviderError(error_msg)
