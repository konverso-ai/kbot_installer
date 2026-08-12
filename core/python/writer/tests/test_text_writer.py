"""Tests for writer.text_writer module."""

from pathlib import Path

from writer.text_writer import TextWriter


def test_write_creates_file_with_content(tmp_path: Path) -> None:
    """It writes the given content to the destination file."""
    writer = TextWriter()
    file_path = tmp_path / "output.txt"

    writer.write("hello world", file_path)

    assert file_path.read_text(encoding="utf-8") == "hello world"


def test_write_accepts_string_path(tmp_path: Path) -> None:
    """It accepts a string path in addition to a Path object."""
    writer = TextWriter()
    file_path = tmp_path / "output.txt"

    writer.write("hello", str(file_path))

    assert file_path.read_text(encoding="utf-8") == "hello"


def test_write_creates_missing_parent_directories(tmp_path: Path) -> None:
    """It creates any missing parent directories before writing."""
    writer = TextWriter()
    file_path = tmp_path / "nested" / "dir" / "output.txt"

    writer.write("content", file_path)

    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == "content"


def test_write_overwrites_existing_file(tmp_path: Path) -> None:
    """It overwrites the content of an existing file."""
    writer = TextWriter()
    file_path = tmp_path / "output.txt"
    file_path.write_text("old content", encoding="utf-8")

    writer.write("new content", file_path)

    assert file_path.read_text(encoding="utf-8") == "new content"


def test_write_defaults_to_utf8_encoding(tmp_path: Path) -> None:
    """It defaults to UTF-8 encoding when none is provided."""
    writer = TextWriter()
    file_path = tmp_path / "output.txt"
    content = "café \u2603"

    writer.write(content, file_path)

    assert file_path.read_bytes() == content.encode("utf-8")


def test_write_accepts_custom_encoding_kwarg(tmp_path: Path) -> None:
    """It honours a custom encoding passed via kwargs."""
    writer = TextWriter()
    file_path = tmp_path / "output.txt"
    content = "café"

    writer.write(content, file_path, encoding="latin-1")

    assert file_path.read_bytes() == content.encode("latin-1")


def test_write_empty_content(tmp_path: Path) -> None:
    """It writes an empty file when content is an empty string."""
    writer = TextWriter()
    file_path = tmp_path / "output.txt"

    writer.write("", file_path)

    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == ""
