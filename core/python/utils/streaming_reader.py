"""Streamed download reader for tar.gz extraction."""

import asyncio
import tarfile
from io import BytesIO
from pathlib import Path
from queue import Empty, Queue
from threading import Event
from typing import IO, cast

import httpx


class StreamingReader:
    """File-like object that reads streamed download chunks from a queue."""

    def __init__(
        self,
        data_queue: Queue[bytes | None],
        download_complete: Event,
        download_error: list[BaseException | None],
        max_buffer_size: int = 4 * 1024 * 1024,
    ) -> None:
        """Set up the reader over a shared queue of downloaded chunks.

        Args:
            data_queue: Queue producing downloaded byte chunks, terminated by `None`.
            download_complete: Event set once the producer has finished (successfully
                or not).
            download_error: One-element list used to smuggle an exception raised by
                the producer back to the reader.
            max_buffer_size: Maximum number of bytes buffered before reads stop
                waiting for more data.

        """
        self._data_queue = data_queue
        self._download_complete = download_complete
        self._download_error = download_error
        self._max_buffer_size = max_buffer_size
        self._buffer = BytesIO()
        self._buffer_pos = 0

    def read(self, size: int = -1) -> bytes:
        """Read bytes from the buffered queue, file-object style.

        Blocks until enough data is available in the queue, the producer signals
        completion, or the internal buffer reaches `max_buffer_size`.

        Args:
            size: Number of bytes to read. If negative, read everything currently
                available.

        Returns:
            The bytes read, which may be shorter than `size` if the stream ended.

        Raises:
            BaseException: The exception raised by the producer, if the stream
                ended in error and no data remains to return.

        """
        if self._buffer_pos > 0:
            remaining = self._buffer.read()
            self._buffer.seek(0)
            self._buffer.truncate(0)
            if remaining:
                self._buffer.write(remaining)
            self._buffer_pos = 0

        current_size = self._buffer.tell()
        available = current_size - self._buffer_pos
        needed = size if size >= 0 and size > available else self._max_buffer_size

        while available < needed and current_size < self._max_buffer_size:
            try:
                chunk = self._data_queue.get(timeout=0.05)
            except Empty:
                if self._download_complete.is_set():
                    break
                continue

            if chunk is None:
                break

            self._buffer.seek(0, 2)
            self._buffer.write(chunk)
            current_size = self._buffer.tell()
            available = current_size - self._buffer_pos

        self._buffer.seek(self._buffer_pos)
        if size < 0:
            result = self._buffer.read()
            self._buffer.seek(0)
            self._buffer.truncate(0)
            self._buffer_pos = 0
        else:
            result = self._buffer.read(size)
            self._buffer_pos = self._buffer.tell()

        if self._download_error[0] and not result:
            raise self._download_error[0]
        return result

    def close(self) -> None:
        """Close the stream."""


def extract_tar_gz_stream(
    data_queue: Queue[bytes | None],
    download_complete: Event,
    download_error: list[BaseException | None],
    target_dir: Path,
    *,
    max_buffer_size: int = 4 * 1024 * 1024,
) -> None:
    """Extract a gzipped tar archive read sequentially from a chunk queue."""
    reader = StreamingReader(
        data_queue,
        download_complete,
        download_error,
        max_buffer_size=max_buffer_size,
    )
    with tarfile.open(fileobj=cast("IO[bytes]", reader), mode="r|gz") as tar:
        for member in tar:
            tar.extract(member, path=target_dir, filter="data")

    if download_error[0]:
        raise download_error[0]


async def stream_download_to_queue(
    client: httpx.AsyncClient,
    endpoint: str,
    data_queue: Queue[bytes | None],
    download_complete: Event,
    download_error: list[BaseException | None],
    *,
    chunk_size: int = 2 * 1024 * 1024,
) -> None:
    """Stream an HTTP GET response into a bounded chunk queue."""
    try:
        async with client.stream("GET", endpoint) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                await asyncio.to_thread(data_queue.put, chunk)
        await asyncio.to_thread(data_queue.put, None)
    except BaseException as exc:
        download_error[0] = exc
        await asyncio.to_thread(data_queue.put, None)
    finally:
        download_complete.set()


async def download_and_extract_tar_gz(
    client: httpx.AsyncClient,
    endpoint: str,
    target_dir: Path,
    *,
    chunk_size: int = 2 * 1024 * 1024,
    max_buffer_size: int = 4 * 1024 * 1024,
    max_queue_size: int = 8,
) -> None:
    """Download a gzipped tar archive and extract it with streaming."""
    target_dir.mkdir(parents=True, exist_ok=True)

    data_queue: Queue[bytes | None] = Queue(maxsize=max_queue_size)
    download_error: list[BaseException | None] = [None]
    download_complete = Event()

    download_task = asyncio.create_task(
        stream_download_to_queue(
            client,
            endpoint,
            data_queue,
            download_complete,
            download_error,
            chunk_size=chunk_size,
        )
    )
    await asyncio.to_thread(
        extract_tar_gz_stream,
        data_queue,
        download_complete,
        download_error,
        target_dir,
        max_buffer_size=max_buffer_size,
    )
    await download_task
