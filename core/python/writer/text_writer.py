"""Text writer implementation."""

from pathlib import Path

from utils.path_utils import ensure_file_path


class TextWriter:
    """Write string content to a file."""

    def write(self, content: str, file_path: str | Path, **kwargs) -> None:
        """Write text content to a file.

        Args:
            content: Text to write.
            file_path: Destination file path.
            **kwargs: Optional arguments forwarded to ``Path.write_text``
                (e.g. ``encoding``, ``errors``, ``newline``). Defaults to
                UTF-8 encoding when ``encoding`` is not provided.

        """
        path = ensure_file_path(file_path)
        write_kwargs = {"encoding": "utf-8", **kwargs}
        path.write_text(content, **write_kwargs)
