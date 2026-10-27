"""Workarea model: the aggregation of installer root, work root, products and rules."""

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from workarea.workarea_rule import WorkareaRule


class Workarea(BaseModel):
    """Aggregation of installer root, work root, installed products, and layout rules.

    Attributes:
        installer_root: Root directory of the installer's own workspace,
            resolved to an absolute path.
        work_root: Root directory of the aggregated workarea produced for
            products, resolved to an absolute path.
        products: Paths to the installed product roots to aggregate.
        rules: Layout rules describing how product files are linked or copied
            into the workarea.

    """

    installer_root: Path
    work_root: Path
    products: list[Path]
    rules: Annotated[list[WorkareaRule], Field(default_factory=list)]

    @field_validator("installer_root", "work_root")
    @classmethod
    def _resolve_root(cls, path: Path) -> Path:
        """Resolve a root to an absolute path.

        Product files are symlinked into the workarea by absolute target, so a
        relative `installer_root` would produce links resolved against their own
        directory instead of the caller's working directory, i.e. broken links.
        """
        return path.resolve()
