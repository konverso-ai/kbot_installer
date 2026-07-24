"""Base writer protocol for serializing models to files."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


class Writer(Protocol):
    """Writer protocol."""

    def write(self, content: str, file_path: str | Path, **kwargs) -> None:
        """Write serialized content to a file.

        Args:
            content: Serialized text to write.
            file_path: Destination file path.
            **kwargs: Optional arguments forwarded to ``Path.write_text``.

        """
