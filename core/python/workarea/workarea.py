"""Workarea model: the aggregation of installer root, work root, products and rules."""

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from workarea.workarea_rule import WorkareaRule


class Workarea(BaseModel):
    installer_root: Path
    work_root: Path
    products: list[Path]
    rules: Annotated[list[WorkareaRule], Field(default_factory=list)]
