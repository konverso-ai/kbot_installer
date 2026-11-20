"""Tests for utils.streaming_reader module."""

import io
import tarfile
from pathlib import Path
from queue import Queue
from threading import Event

import httpx
import pytest

from utils.streaming_reader import (
    StreamingReader,
    download_and_extract_tar_gz,
    extract_tar_gz_stream,
    stream_download_to_queue,
)
from utils.utils_for_unit_tests import compare


def _build_tar_gz(content: bytes, name: str = "hello.txt") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def _feed_queue(queue: Queue[bytes | None], payload: bytes, chunk_size: int) -> None:
    for offset in range(0, len(payload), chunk_size):
        queue.put(payload[offset : offset + chunk_size])
    queue.put(None)


def test_read_valid_returns_all_queued_bytes() -> None:
    queue: Queue[bytes | None] = Queue()
    queue.put(b"hello")
    queue.put(None)
    download_complete = Event()
    download_complete.set()
    download_error: list[BaseException | None] = [None]

    reader = StreamingReader(queue, download_complete, download_error)
    assert compare("eq", reader.read(), b"hello")
    assert compare("eq", reader.read(), b"")


def test_read_valid_returns_partial_reads() -> None:
    queue: Queue[bytes | None] = Queue()
    queue.put(b"abcdef")
    queue.put(None)
    download_complete = Event()
    download_complete.set()
    download_error: list[BaseException | None] = [None]

    reader = StreamingReader(queue, download_complete, download_error, max_buffer_size=1024)
    assert compare("eq", reader.read(3), b"abc")
    assert compare("eq", reader.read(3), b"def")
    assert compare("eq", reader.read(), b"")


def test_read_invalid_raises_download_error_when_empty() -> None:
    queue: Queue[bytes | None] = Queue()
    queue.put(None)
    download_complete = Event()
    download_complete.set()
    download_error: list[BaseException | None] = [ValueError("download failed")]

    reader = StreamingReader(queue, download_complete, download_error)

    with pytest.raises(ValueError):
        reader.read()


def test_extracttargzstream_valid_extracts_chunked_archive(tmp_path: Path) -> None:
    archive = _build_tar_gz(b"hello", name="hello.txt")
    queue: Queue[bytes | None] = Queue()
    _feed_queue(queue, archive, chunk_size=64)
    download_complete = Event()
    download_complete.set()
    download_error: list[BaseException | None] = [None]

    extract_tar_gz_stream(queue, download_complete, download_error, tmp_path)

    assert compare("eq", (tmp_path / "hello.txt").read_bytes(), b"hello")


def test_extracttargzstream_invalid_raises_download_error(tmp_path: Path) -> None:
    queue: Queue[bytes | None] = Queue()
    queue.put(None)
    download_complete = Event()
    download_complete.set()
    download_error: list[BaseException | None] = [RuntimeError("network error")]

    with pytest.raises(RuntimeError):
        extract_tar_gz_stream(queue, download_complete, download_error, tmp_path)


@pytest.mark.asyncio
async def test_streamdownloadtoqueue_valid_fills_queue() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/file.bin":
            return httpx.Response(200, content=b"chunk-data")
        return httpx.Response(404)

    queue: Queue[bytes | None] = Queue()
    download_complete = Event()
    download_error: list[BaseException | None] = [None]

    async with httpx.AsyncClient(
        base_url="https://example.com",
        transport=httpx.MockTransport(handler),
    ) as client:
        await stream_download_to_queue(
            client,
            "file.bin",
            queue,
            download_complete,
            download_error,
            chunk_size=4,
        )

    chunks: list[bytes] = []
    while True:
        item = queue.get()
        if item is None:
            break
        chunks.append(item)

    assert compare("eq", b"".join(chunks), b"chunk-data")
    assert compare("eq", download_error[0], None)
    assert compare("eq", download_complete.is_set(), True)


@pytest.mark.asyncio
async def test_streamdownloadtoqueue_invalid_records_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    queue: Queue[bytes | None] = Queue()
    download_complete = Event()
    download_error: list[BaseException | None] = [None]

    async with httpx.AsyncClient(
        base_url="https://example.com",
        transport=httpx.MockTransport(handler),
    ) as client:
        await stream_download_to_queue(
            client,
            "missing.bin",
            queue,
            download_complete,
            download_error,
        )

    assert compare("ne", download_error[0], None)
    assert compare("eq", download_complete.is_set(), True)
    assert compare("eq", queue.get(), None)


@pytest.mark.asyncio
async def test_downloadandextracttargz_valid_extracts_streamed_archive(tmp_path: Path) -> None:
    archive = _build_tar_gz(b"streamed", name="streamed.txt")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/archives/pkg.tar.gz":
            return httpx.Response(200, content=archive)
        return httpx.Response(404)

    async with httpx.AsyncClient(
        base_url="https://example.com",
        transport=httpx.MockTransport(handler),
    ) as client:
        await download_and_extract_tar_gz(
            client,
            "archives/pkg.tar.gz",
            tmp_path,
            chunk_size=64,
        )

    assert compare("eq", (tmp_path / "streamed.txt").read_bytes(), b"streamed")


@pytest.mark.asyncio
async def test_downloadandextracttargz_invalid_raises_http_error(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(
        base_url="https://example.com",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await download_and_extract_tar_gz(client, "archives/missing.tar.gz", tmp_path)
