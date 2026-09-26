"""Structured working-tree status of a git repository."""

from pydantic import BaseModel, Field

__all__ = ["RepoStatus"]


class RepoStatus(BaseModel):
    """Snapshot of a repository's staged, unstaged and untracked paths.

    Replaces the GitPython idioms ``repo.index.diff("HEAD")`` (staged),
    ``repo.index.diff(None)`` (unstaged) and ``repo.untracked_files``.

    All paths are repository-relative and decoded to ``str``.
    """

    staged_added: list[str] = Field(default_factory=list)
    staged_deleted: list[str] = Field(default_factory=list)
    staged_modified: list[str] = Field(default_factory=list)
    unstaged: list[str] = Field(default_factory=list)
    untracked: list[str] = Field(default_factory=list)

    @property
    def staged(self) -> list[str]:
        """All staged paths, whatever the kind of change."""
        return [*self.staged_added, *self.staged_deleted, *self.staged_modified]

    @property
    def has_staged_changes(self) -> bool:
        """True when the index holds changes ready to be committed."""
        return bool(self.staged)

    @property
    def is_clean(self) -> bool:
        """True when the repository has no staged, unstaged or untracked change."""
        return not (self.staged or self.unstaged or self.untracked)

    @property
    def changed(self) -> list[str]:
        """Staged and unstaged paths, excluding untracked ones.

        Mirrors the ``check_uncommitted`` notion of "uncommitted changes".
        """
        return sorted(set(self.staged) | set(self.unstaged))
