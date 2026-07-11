"""Base writer protocol for serializing models to files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Writer(Protocol):
    """Writer protocol."""

    def write(self, content: str, file_path: str | Path, **kwargs: Any) -> None:
        """Write serialized content to a file.

        Args:
            content: Serialized text to write.
            file_path: Destination file path.
            **kwargs: Optional arguments forwarded to ``Path.write_text``.

        """
