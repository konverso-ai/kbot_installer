"""Branch-fallback cloning for a single provider.

Given one provider and an ordered list of candidate branches (the requested
branch followed by the provider's configured fallbacks), try to clone using
each branch in turn until one succeeds. This is a "single provider, several
branches" concern, distinct from ``SelectorProvider``'s "several providers"
concern.
"""

from pathlib import Path
from typing import Protocol, cast

from git.provider.base import ProviderBase
from git.provider.config import ProviderConfig, ProvidersConfig
from git.provider.errors import ProviderError
from git.provider.git_provider_base import GitProviderBase


class _ProviderConfigLookup(Protocol):
    """Structural type for config objects exposing ``get_provider_config``.

    Used to type-narrow ``config`` after the ``hasattr`` duck-typing check
    below, since real callers may pass a ``ProvidersConfig``, a mock, or a
    plain dict (accepted by tests that don't need real branch fallback
    behavior).
    """

    def get_provider_config(self, provider_name: str) -> ProviderConfig | None:
        """Return the provider config for the given provider name, if any."""


def get_branches_to_try(
    config: ProvidersConfig | dict[str, object],
    provider_name: str,
    branch: str | None,
) -> list[str]:
    """Get the ordered list of branches to try for a provider.

    Args:
        config: Full providers configuration (or a plain dict, accepted for
            tests that don't need real branch fallback behavior).
        provider_name: Name of the provider to look up configured fallback
            branches for.
        branch: Branch explicitly requested by the caller, or None to use
            the provider's configured branches as-is.

    Returns:
        Branches to try in order: the requested branch first (if any),
        followed by configured fallback branches, without duplicates.

    """
    provider_config = (
        cast("_ProviderConfigLookup", config).get_provider_config(provider_name)
        if hasattr(config, "get_provider_config")
        else None
    )
    configured_branches = (
        list(provider_config.branches)
        if provider_config is not None and provider_config.branches
        else []
    )

    if not branch:
        return configured_branches
    return list(dict.fromkeys([branch, *configured_branches]))


def _is_branch_not_found_error(error: Exception) -> bool:
    """Return whether an error looks like a missing branch/version."""
    error_str = str(error).lower()
    return "not found" in error_str or "branch" in error_str or "version" in error_str


def _clone_kwargs(repository_identifier: str, *, by_url: bool) -> dict[str, str]:
    """Build the ``repository_url``/``repository_name`` kwarg for a clone call."""
    return (
        {"repository_url": repository_identifier}
        if by_url
        else {"repository_name": repository_identifier}
    )


def _select_remote_branch(
    provider: GitProviderBase, repository_url: str, branches: list[str]
) -> str | None:
    """Pick the first candidate branch that exists on the remote.

    Raises:
        ProviderError: If none of the candidate branches exist remotely.

    """
    if not branches:
        return None

    remote_branches = provider.list_remote_branches(repository_url)
    for branch in branches:
        if branch in remote_branches:
            return branch

    requested = ", ".join(f"'{branch}'" for branch in branches)
    available = ", ".join(remote_branches) if remote_branches else "none"
    msg = (
        f"Branch(es) {requested} not found on remote repository "
        f"'{repository_url}'. Available branches: {available}"
    )
    raise ProviderError(msg)


def _clone_with_branch_fallback_git(
    provider: GitProviderBase,
    repository_identifier: str,
    target_path: Path,
    branches: list[str],
    *,
    by_url: bool,
) -> str:
    """Clone with a git provider, checking branch existence remotely first."""
    repository_url = (
        repository_identifier
        if by_url
        else provider.build_repository_url(repository_identifier)
    )
    branch_to_use = _select_remote_branch(provider, repository_url, branches)
    provider.clone_and_checkout(
        target_path, branch_to_use, **_clone_kwargs(repository_identifier, by_url=by_url)
    )
    return branch_to_use or ""


def _attempt_clone_branch(
    provider: ProviderBase,
    branch: str,
    target_path: Path,
    clone_kwargs: dict[str, str],
    *,
    commit: str | None,
    is_last_branch: bool,
) -> ProviderError | None:
    """Try cloning a single candidate branch.

    Returns:
        None on success, or the retryable ``ProviderError`` encountered.

    Raises:
        ProviderError: If the failure is not retryable with another branch.

    """
    try:
        provider.clone_and_checkout(target_path, branch, commit=commit, **clone_kwargs)
    except ProviderError as e:
        if _is_branch_not_found_error(e) and not is_last_branch:
            return e
        raise
    return None


def _clone_with_branch_fallback_generic(
    provider: ProviderBase,
    repository_identifier: str,
    target_path: Path,
    branches: list[str],
    *,
    by_url: bool,
    commit: str | None,
) -> str:
    """Clone with a non-git provider, trying candidate branches in order."""
    clone_kwargs = _clone_kwargs(repository_identifier, by_url=by_url)
    last_error: ProviderError | None = None

    for branch in branches:
        error = _attempt_clone_branch(
            provider,
            branch,
            target_path,
            clone_kwargs,
            commit=commit,
            is_last_branch=branch == branches[-1],
        )
        if error is None:
            return branch
        last_error = error

    if last_error:
        raise last_error
    error_msg = (
        f"Failed to download repository with any branch from fallback list: {branches}"
    )
    raise ProviderError(error_msg)


def clone_with_branch_fallback(
    provider: ProviderBase,
    repository_identifier: str,
    target_path: Path,
    branches: list[str],
    *,
    by_url: bool,
    commit: str | None = None,
) -> str:
    """Clone a repository with a single provider, trying candidate branches.

    Args:
        provider: Provider instance to clone with.
        repository_identifier: Repository URL or name (see ``by_url``).
        target_path: Local path where the repository should be cloned.
        branches: Candidate branches in priority order. May be empty to use
            the provider's default branch.
        by_url: Whether ``repository_identifier`` is a repository URL
            (True) or a repository name (False).
        commit: Specific commit to pin the checkout to, when supported by
            the provider.

    Returns:
        The branch that was used, or ``""`` if none was requested/needed.

    Raises:
        ProviderError: If every candidate branch fails.

    """
    if isinstance(provider, GitProviderBase):
        return _clone_with_branch_fallback_git(
            provider, repository_identifier, target_path, branches, by_url=by_url
        )
    return _clone_with_branch_fallback_generic(
        provider,
        repository_identifier,
        target_path,
        branches,
        by_url=by_url,
        commit=commit,
    )
