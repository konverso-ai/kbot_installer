from pathlib import Path
from typing import Annotated

from pydantic import Field, RootModel
from typing_extensions import override
from utils.work_in_progress import JsonModel
from workarea.rule_action import RuleAction


class WorkareaRule(JsonModel):
    source: Path
    target: Annotated[Path | None, Field(default=None)]
    action: RuleAction

    recursive: Annotated[bool, Field(default=True)]

    includes: Annotated[list[str], Field(default_factory=list)]
    excludes: Annotated[list[str], Field(default_factory=list)]

    placeholders: Annotated[list[str], Field(default_factory=list)]

    def target_path(self) -> Path:
        return self.target or self.source


class WorkareaRules(RootModel[list[WorkareaRule]], JsonModel):
    @override
    def __iter__(self):
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __getitem__(self, index: int) -> WorkareaRule:
        return self.root[index]
