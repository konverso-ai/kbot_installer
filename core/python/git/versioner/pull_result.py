"""Structured outcome of a pull operation."""

from pydantic import BaseModel, Field

__all__ = ["PullResult"]


class PullResult(BaseModel):
    """Paths affected by a pull, as a structured diff of HEAD before/after.

    Replaces the parsing of ``git pull`` textual output (``"N files changed"``,
    ``"delete mode 100644 <path>"``). All paths are repository-relative and
    decoded to ``str``.

    Renames are reported as a deletion plus an addition, which is what callers
    tracking removed files need.
    """

    old_commit_id: str | None = None
    new_commit_id: str | None = None
    added: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    deleted: list[str] = Field(default_factory=list)

    @property
    def changed(self) -> list[str]:
        """All affected paths, sorted and de-duplicated."""
        return sorted(set(self.added) | set(self.modified) | set(self.deleted))

    @property
    def has_changes(self) -> bool:
        """True when the pull brought at least one file change."""
        return bool(self.added or self.modified or self.deleted)

    @property
    def is_fast_forward_noop(self) -> bool:
        """True when HEAD did not move at all."""
        return self.old_commit_id == self.new_commit_id
