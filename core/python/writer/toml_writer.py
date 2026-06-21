"""TOML writer implementation."""

from pathlib import Path

import tomlkit
from pydantic import BaseModel

from utils.path_utils import ensure_path


class TomlWriter:
    """Serialize Pydantic models to TOML files."""

    def write(self, obj: BaseModel, file_path: str | Path) -> None:
        """Write a model instance to a TOML file.

        Args:
            obj: Model instance to serialize.
            file_path: Destination TOML file path.
        """
        doc = tomlkit.document()
        doc.update(obj.model_dump(mode="python", exclude_none=True))
        path = ensure_path(file_path)
        with path.open(mode="w", encoding="utf-8") as file:
            tomlkit.dump(doc, file)
