"""Workarea model: the aggregation of installer root, work root, products and rules."""

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from workarea.workarea_rule import WorkareaRule


class Workarea(BaseModel):
    """Aggregation of installer root, work root, installed products, and layout rules.

    Attributes:
        installer_root: Root directory of the installer's own workspace.
        work_root: Root directory of the aggregated workarea produced for products.
        products: Paths to the installed product roots to aggregate.
        rules: Layout rules describing how product files are linked or copied
            into the workarea.

    """

    installer_root: Path
    work_root: Path
    products: list[Path]
    rules: Annotated[list[WorkareaRule], Field(default_factory=list)]
