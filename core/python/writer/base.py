"""Base writer protocol for serializing models to files."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class Writer(Protocol):
    """Writer protocol."""

    def write(self, obj: BaseModel, file_path: str | Path) -> None:
        """Write a model instance to a file.

        Args:
            obj: Model instance to serialize.
            file_path: Destination file path.
        """
