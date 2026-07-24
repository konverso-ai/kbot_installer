"""Workarea layout rule model describing how product paths map onto a workarea."""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from pydantic import Field, RootModel
from typing_extensions import override

from utils.work_in_progress import JsonModel
from workarea.rule_action import RuleAction


class WorkareaRule(JsonModel):
    """Single rule mapping a product source path onto a workarea target path.

    Attributes:
        source: Path, relative to the product root, of the source to process.
        target: Path, relative to the work root, to write to. Defaults to
            `source` when unset.
        action: How the source is applied to the target (link, copy, ignore).
        recursive: Whether to recurse into subdirectories when collecting
            source paths.
        includes: Glob patterns a relative source path must match to be kept.
            If empty, all paths are kept.
        excludes: Glob patterns a relative source path must not match.
        placeholders: Names of runtime variables to render into copied file
            contents.

    """

    source: Path
    target: Annotated[Path | None, Field(default=None)]
    action: RuleAction

    recursive: Annotated[bool, Field(default=True)]

    includes: Annotated[list[str], Field(default_factory=list)]
    excludes: Annotated[list[str], Field(default_factory=list)]

    placeholders: Annotated[list[str], Field(default_factory=list)]

    def target_path(self) -> Path:
        """Return the target path, falling back to the source path.

        Returns:
            The configured `target` path, or `source` if no target is set.

        """
        return self.target or self.source


class WorkareaRules(RootModel[list[WorkareaRule]], JsonModel):
    """List-like collection of `WorkareaRule` items, backed by a root list."""

    @override
    def __iter__(self) -> Iterator[WorkareaRule]:
        return iter(self.root)

    def __len__(self) -> int:
        """Return the number of rules in the collection.

        Returns:
            The number of `WorkareaRule` items.

        """
        return len(self.root)

    def __getitem__(self, index: int) -> WorkareaRule:
        """Return the rule at the given index.

        Args:
            index: Position of the rule to retrieve.

        Returns:
            The `WorkareaRule` at `index`.

        """
        return self.root[index]
