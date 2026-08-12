"""Tests for service.nexus_files module."""

from unittest.mock import MagicMock

from service.nexus_file import NexusFile
from service.nexus_files import NexusFiles
from utils.utils_for_unit_tests import compare


def _make_file(**overrides) -> NexusFile:
    return NexusFile.from_json(overrides, service=MagicMock())


class TestNexusFiles:
    """Test cases for NexusFiles class."""

    def test_fromjson_valid_builds_files_and_token(self) -> None:
        """Test from_json builds NexusFile items and keeps the continuation token."""
        service = MagicMock()
        data = {
            "items": [{"path": "/repo/a.txt"}, {"path": "/repo/b.txt"}],
            "continuationToken": "tok-1",
        }

        files = NexusFiles.from_json(data, service=service)

        assert compare("eq", len(files), 2)
        assert compare("eq", files.continuation_token, "tok-1")
        assert compare("eq", files._service, service)

    def test_fromjson_valid_handles_missing_items(self) -> None:
        """Test from_json defaults to an empty file list when items are absent."""
        files = NexusFiles.from_json({}, service=MagicMock())

        assert compare("eq", len(files), 0)
        assert compare("eq", files.continuation_token, None)

    def test_empty_valid_returns_instance_bound_to_service(self) -> None:
        """Test empty returns a NexusFiles instance with no files, bound to a service."""
        service = MagicMock()

        files = NexusFiles.empty(service=service)

        assert compare("eq", len(files), 0)
        assert compare("eq", files._service, service)

    def test_extendfromjson_valid_appends_files_and_updates_token(self) -> None:
        """Test extend_from_json appends files and replaces the continuation token."""
        service = MagicMock()
        files = NexusFiles.empty(service=service)

        files.extend_from_json({"items": [{"path": "/repo/a.txt"}], "continuationToken": "tok-1"})
        files.extend_from_json({"items": [{"path": "/repo/b.txt"}], "continuationToken": None})

        assert compare("eq", len(files), 2)
        assert compare("eq", files.continuation_token, None)

    def test_filter_valid_by_folder_name(self) -> None:
        """Test filter narrows files by exact folder name."""
        files = NexusFiles(
            files=[
                _make_file(path="/folder_a/one.txt"),
                _make_file(path="/folder_b/two.txt"),
            ]
        )

        filtered = files.filter(folder_name="folder_a")

        assert compare("eq", [f.path for f in filtered], ["/folder_a/one.txt"])

    def test_filter_valid_by_folder_starts_with(self) -> None:
        """Test filter narrows files by a folder name prefix."""
        files = NexusFiles(
            files=[
                _make_file(path="/releases/app/one.txt"),
                _make_file(path="/other/two.txt"),
            ]
        )

        filtered = files.filter(folder_starts_with="releases")

        assert compare("eq", [f.path for f in filtered], ["/releases/app/one.txt"])

    def test_filter_valid_by_name(self) -> None:
        """Test filter narrows files by exact file name."""
        files = NexusFiles(
            files=[
                _make_file(path="/folder/one.txt"),
                _make_file(path="/folder/two.txt"),
            ]
        )

        filtered = files.filter(name="two.txt")

        assert compare("eq", [f.path for f in filtered], ["/folder/two.txt"])

    def test_filter_valid_by_ends_with(self) -> None:
        """Test filter narrows files by file name suffix."""
        files = NexusFiles(
            files=[
                _make_file(path="/folder/one.tar.gz"),
                _make_file(path="/folder/two.txt"),
            ]
        )

        filtered = files.filter(ends_with=".tar.gz")

        assert compare("eq", [f.path for f in filtered], ["/folder/one.tar.gz"])

    def test_filter_valid_by_not_ends_with(self) -> None:
        """Test filter excludes files matching a file name suffix."""
        files = NexusFiles(
            files=[
                _make_file(path="/folder/one.tar.gz"),
                _make_file(path="/folder/two.txt"),
            ]
        )

        filtered = files.filter(not_ends_with=".tar.gz")

        assert compare("eq", [f.path for f in filtered], ["/folder/two.txt"])

    def test_filter_valid_by_contains(self) -> None:
        """Test filter narrows files whose path contains a substring."""
        files = NexusFiles(
            files=[
                _make_file(path="/folder/release-1.0.tar.gz"),
                _make_file(path="/folder/other.tar.gz"),
            ]
        )

        filtered = files.filter(contains="release")

        assert compare("eq", [f.path for f in filtered], ["/folder/release-1.0.tar.gz"])

    def test_filter_valid_combines_criteria(self) -> None:
        """Test filter applies multiple criteria together."""
        files = NexusFiles(
            files=[
                _make_file(path="/releases/app/one.tar.gz"),
                _make_file(path="/releases/app/one.txt"),
                _make_file(path="/other/two.tar.gz"),
            ]
        )

        filtered = files.filter(folder_starts_with="releases", ends_with=".tar.gz")

        assert compare("eq", [f.path for f in filtered], ["/releases/app/one.tar.gz"])

    def test_filter_valid_preserves_service_reference(self) -> None:
        """Test filter propagates the bound service to the resulting collection."""
        service = MagicMock()
        files = NexusFiles.empty(service=service)

        filtered = files.filter(name="missing.txt")

        assert compare("eq", filtered._service, service)

    def test_filter_valid_returns_empty_when_no_match(self) -> None:
        """Test filter returns an empty collection when nothing matches."""
        files = NexusFiles(files=[_make_file(path="/folder/one.txt")])

        filtered = files.filter(name="missing.txt")

        assert compare("eq", len(filtered), 0)

    def test_latest_valid_returns_none_when_empty(self) -> None:
        """Test latest returns None for an empty collection."""
        files = NexusFiles.empty(service=MagicMock())

        assert compare("eq", files.latest(), None)

    def test_latest_valid_returns_most_recently_modified(self) -> None:
        """Test latest returns the file with the most recent last_modified value."""
        oldest = _make_file(path="/folder/old.txt", lastModified="2024-01-01T00:00:00Z")
        newest = _make_file(path="/folder/new.txt", lastModified="2024-06-01T00:00:00Z")
        files = NexusFiles(files=[oldest, newest])

        assert compare("eq", files.latest(), newest)

    def test_latest_valid_treats_missing_last_modified_as_oldest(self) -> None:
        """Test latest ranks files without last_modified below dated files."""
        undated = _make_file(path="/folder/undated.txt")
        dated = _make_file(path="/folder/dated.txt", lastModified="2024-01-01T00:00:00Z")
        files = NexusFiles(files=[undated, dated])

        assert compare("eq", files.latest(), dated)

    def test_iter_valid_yields_files(self) -> None:
        """Test __iter__ yields the underlying files in order."""
        first = _make_file(path="/folder/a.txt")
        second = _make_file(path="/folder/b.txt")
        files = NexusFiles(files=[first, second])

        assert compare("eq", list(files), [first, second])

    def test_len_valid_returns_file_count(self) -> None:
        """Test __len__ returns the number of files in the collection."""
        files = NexusFiles(
            files=[_make_file(path="/folder/a.txt"), _make_file(path="/folder/b.txt")]
        )

        assert compare("eq", len(files), 2)
