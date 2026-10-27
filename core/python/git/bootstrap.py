"""Bootstrap a versioned git repository from a GitRepo model."""

from pathlib import Path

from git.io import write_repository
from git.models import GitRepo
from git.versioner import VersionerBase
from utils.version import Version


def bootstrap_repository(
    repo: GitRepo,
    versioner: VersionerBase,
    path: str | Path,
    versions: list[Version],
) -> None:
    """Bootstrap the repository."""
    branches: list[str] = []
    for version in versions:
        new_branch = version.to_branch(with_env=True)
        versioner.checkout(path, new_branch)
        write_repository(repo, path)
        versioner.add(path)
        versioner.commit(path, f"chore: initial commit for {new_branch}")
        branches.append(new_branch)
    versioner.push_branches(path, branches)
