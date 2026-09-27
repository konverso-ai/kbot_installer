"""Shared helpers for storage download operations."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import IO, TYPE_CHECKING, cast

from installer_support.installer_utils import extract_tar_member
from utils.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

log = logger.get_package_logger("storage")


class SystemTarError(RuntimeError):
    """Raised when the system ``tar`` fails to extract a streamed archive."""


def extract_tar_gz_archive(archive_path: Path, target_dir: Path) -> None:
    """Extract a ``.tar.gz`` archive, preferring the system ``tar`` when available."""
    target_dir.mkdir(parents=True, exist_ok=True)
    tar_bin = shutil.which("tar")
    if tar_bin is not None:
        result = subprocess.run(  # noqa: S603
            [tar_bin, "-xzf", str(archive_path), "-C", str(target_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return

        details = (result.stderr or result.stdout or "").strip()
        log.warning(
            "System tar extraction failed (exit %s), falling back to Python: %s",
            result.returncode,
            details,
        )

    _extract_tar_gz_with_python(archive_path, target_dir)


def _extract_tar_gz_with_python(archive_path: Path, target_dir: Path) -> None:
    """Extract a ``.tar.gz`` archive with Python tarfile and symlink handling."""
    with tarfile.open(archive_path, mode="r:gz") as tar:
        for member in tar:
            extract_tar_member(tar, member, target_dir)


@contextmanager
def system_tar_gz_extractor(tar_bin: str, target_dir: Path) -> Iterator[IO[bytes]]:
    """Yield a pipe whose ``.tar.gz`` content is extracted on the fly by ``tar``.

    Extraction overlaps with the download and no temporary archive is written
    to disk, which matters for large products (e.g. ``3rdparty``).

    Args:
        tar_bin: Path to the system ``tar`` executable.
        target_dir: Directory the archive is extracted into.

    Yields:
        A binary stream to write the gzipped tar archive into.

    Raises:
        SystemTarError: If ``tar`` exits with an error.

    """
    # stderr goes to a file: a pipe could fill up with warnings and block tar
    # while we are blocked writing to its stdin.
    with tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(  # noqa: S603
            [tar_bin, "-xzf", "-", "-C", str(target_dir)],
            stdin=subprocess.PIPE,
            stderr=stderr_file,
        )
        stdin = cast("IO[bytes]", process.stdin)

        def tar_error() -> SystemTarError:
            stderr_file.seek(0)
            details = stderr_file.read().decode(errors="replace").strip()
            return SystemTarError(f"tar exited with code {process.returncode}: {details}")

        try:
            yield stdin
        except BaseException as exc:
            # A broken pipe means tar died first: its error is the real cause.
            if isinstance(exc, BrokenPipeError) or process.poll() is not None:
                process.wait()
                if process.returncode != 0:
                    raise tar_error() from exc
            else:
                process.kill()
                process.wait()
            raise
        finally:
            with suppress(BrokenPipeError):
                stdin.close()

        if process.wait() != 0:
            raise tar_error()


def download_and_extract_tar_gz(
    download_to: Callable[[str, IO[bytes]], None],
    key: str,
    target_dir: Path,
) -> None:
    """Download a tar.gz object and extract it into ``target_dir``.

    The download is streamed straight into the system ``tar`` when available.
    If ``tar`` is missing or fails (e.g. case conflicts, absolute symlinks), the
    archive is downloaded to a temporary file and extracted with Python.

    Args:
        download_to: Callable writing the object identified by its first
            argument into the binary stream given as second argument.
        key: Object key of the archive.
        target_dir: Directory the archive is extracted into.

    """
    target_dir.mkdir(parents=True, exist_ok=True)

    tar_bin = shutil.which("tar")
    if tar_bin is not None:
        try:
            with system_tar_gz_extractor(tar_bin, target_dir) as stream:
                download_to(key, stream)
        except SystemTarError as exc:
            log.warning(
                "Streamed tar extraction of '%s' failed, downloading it again to extract with Python: %s",
                key,
                exc,
            )
        else:
            return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as temp_file:
        temp_path = Path(temp_file.name)

    try:
        with temp_path.open("wb") as archive:
            download_to(key, archive)
        _extract_tar_gz_with_python(temp_path, target_dir)
    finally:
        temp_path.unlink(missing_ok=True)
