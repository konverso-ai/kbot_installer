"""Utility functions for kbot-installer."""

import logging
import os
import tarfile
import tempfile
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from queue import Queue
from tempfile import SpooledTemporaryFile
from threading import Event, Thread

import requests

logger = logging.getLogger(__name__)


def version_to_branch(version: str) -> str:
    """Convert a version string to a Git branch name.

    Args:
        version: Version string (e.g., '2025.03', 'dev', 'master', '2025.03-dev').

    Returns:
        Git branch name corresponding to the version.

    Examples:
        >>> version_to_branch("dev")
        "dev"
        >>> version_to_branch("master")
        "master"
        >>> version_to_branch("2025.03")
        "release-2025.03"
        >>> version_to_branch("2025.03-dev")
        "release-2025.03-dev"

    """
    if version == "dev":
        return "dev"
    if version == "master":
        return "master"
    if version.endswith("-dev"):
        # 2025.03-dev → release-2025.03-dev
        base_version = version[:-4]  # Remove "-dev"
        return f"release-{base_version}-dev"
    # 2025.03 → release-2025.03
    return f"release-{version}"


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory.

    Returns:
        Path object of the directory.

    Raises:
        OSError: If the directory cannot be created.

    """
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def optimized_download_and_extract(
    url: str, target_dir: Path, auth_obj: object | None = None
) -> None:
    """Optimized download and extract using benchmark results.

    Uses the most efficient method: streaming download with 4MB chunks
    and direct extraction without temporary file when possible.

    Args:
        url: URL to download the tar.gz file from.
        target_dir: Target directory for extraction.
        auth_obj: Authentication object for download.

    Raises:
        httpx.HTTPError: If the HTTP request fails.
        tarfile.TarError: If the tar file is corrupted or invalid.
        OSError: If there are issues with file system operations during extraction.

    """
    # Import httpx locally to avoid heavy import at module level
    import httpx  # noqa: PLC0415

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    # Stream download and extract in one pass (most efficient method)
    with httpx.stream("GET", url, timeout=60.0, auth=auth_obj) as response:
        response.raise_for_status()

        # Create tarfile from stream with optimal chunk size (4MB from benchmark)
        # Simple approach: download to temp file then extract

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Stream download to temp file
            for chunk in response.iter_bytes(chunk_size=16 * 1024 * 1024):
                temp_file.write(chunk)
            temp_file.flush()

            # Extract from temp file
            with tarfile.open(temp_file.name, mode="r:gz") as tar:
                for member in tar:
                    tar.extract(member, path=target_dir, filter="data")

            # Clean up temp file
            Path(temp_file.name).unlink()

    logger.info(
        "Successfully downloaded and extracted from %s to %s",
        url,
        target_dir,
    )


def optimized_download_and_extract_bis(
    url: str, target_dir: Path, auth_obj: object | None = None
) -> None:
    """Télécharge et extrait en parallèle avec threading.

    L'extraction commence dès que suffisamment de données sont disponibles.
    """
    # Import httpx locally to avoid heavy import at module level
    import httpx  # noqa: PLC0415

    target_dir.mkdir(parents=True, exist_ok=True)

    buffer = SpooledTemporaryFile(max_size=100 * 1024 * 1024)  # noqa: SIM115
    queue = Queue(maxsize=1)  # Synchronisation

    def download_worker() -> None:
        """Thread de téléchargement."""
        try:
            with httpx.stream("GET", url, timeout=60.0, auth=auth_obj) as response:
                response.raise_for_status()

                for chunk in response.iter_bytes(chunk_size=16 * 1024 * 1024):
                    buffer.write(chunk)
                    buffer.flush()

                    # Signaler qu'on a des données
                    if buffer.tell() > 10 * 1024 * 1024:  # Attendre 10MB
                        queue.put("ready")

            queue.put("done")
        except Exception as e:
            queue.put(("error", e))

    # Lancer le téléchargement en parallèle
    download_thread = Thread(target=download_worker, daemon=True)
    download_thread.start()

    # Attendre que le téléchargement démarre
    queue.get()

    # Commencer l'extraction pendant le téléchargement
    buffer.seek(0)
    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        for member in tar:
            tar.extract(member, path=target_dir, filter="data")

    # Attendre la fin du téléchargement
    download_thread.join()
    buffer.close()

    logger.info("Successfully downloaded and extracted from %s to %s", url, target_dir)


def calculate_relative_path(src: Path, dst: Path) -> Path:
    """Calculate relative path from destination to source.

    Args:
        src: Source path.
        dst: Destination path.

    Returns:
        Relative path from dst to src.

    """
    src_abs = Path(src).resolve()
    dst_abs = Path(dst).resolve()

    try:
        return Path(os.path.relpath(src_abs, dst_abs.parent))
    except Exception:
        # If relpath fails (e.g., different drives on some OS), return absolute
        return src_abs


def optimized_download_and_extract_ter(  # noqa: C901
    url: str, target_dir: Path, auth_obj: object | None = None
) -> None:
    """Download and extract a tar.gz file with true streaming and minimal memory.

    Uses a producer-consumer pattern with a bounded queue to stream data
    directly from the network to tarfile extraction. The extraction starts
    as soon as enough data is available, preventing memory accumulation.

    Args:
        url: URL to download the tar.gz file from.
        target_dir: Target directory for extraction.
        auth_obj: Authentication object for download.

    Raises:
        httpx.HTTPError: If the HTTP request fails.
        tarfile.TarError: If the tar file is corrupted or invalid.
        OSError: If there are issues with file system operations during extraction.

    """
    # Import httpx locally to avoid heavy import at module level
    import httpx  # noqa: PLC0415

    target_dir.mkdir(parents=True, exist_ok=True)

    # Optimized parameters for better throughput:
    # - Larger chunks reduce network syscalls (2MB instead of 512KB)
    # - Larger queue allows better pipelining (8 chunks = 16MB buffer)
    # - Larger reader buffer reduces fragmentation (4MB)
    max_queue_size = 8  # Increased for better pipelining
    chunk_size = 2 * 1024 * 1024  # 2MB chunks for better network efficiency
    max_buffer_size = 4 * 1024 * 1024  # 4MB buffer to reduce fragmentation

    data_queue: Queue[bytes | None] = Queue(maxsize=max_queue_size)
    download_error: Exception | None = None
    download_complete = Event()

    def download_worker() -> None:
        """Download chunks and put them in queue with backpressure."""
        nonlocal download_error
        try:
            with httpx.stream("GET", url, timeout=60.0, auth=auth_obj) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    data_queue.put(chunk)
            data_queue.put(None)  # Signal end of stream
            download_complete.set()
        except Exception as e:
            download_error = e
            data_queue.put(None)  # Signal error
            download_complete.set()

    # Start download thread
    download_thread = Thread(target=download_worker, daemon=True)
    download_thread.start()

    try:
        # Stream reader optimized to minimize seeks and copies
        class StreamingReader:
            """File-like object that reads from the queue with optimized buffering."""

            def __init__(self) -> None:
                # Use BytesIO for efficient buffering, but optimize usage
                self.buffer = BytesIO()
                self.buffer_pos = 0  # Track read position

            def read(self, size: int = -1) -> bytes:
                """Read data from queue, optimized to minimize seeks."""
                # Calculate available data without excessive seeks
                if self.buffer_pos > 0:
                    # We've consumed data, need to compact buffer
                    remaining = self.buffer.read()
                    self.buffer.seek(0)
                    self.buffer.truncate(0)
                    if remaining:
                        self.buffer.write(remaining)
                    self.buffer_pos = 0

                current_size = self.buffer.tell()
                available = current_size - self.buffer_pos

                # Fill buffer from queue if needed
                needed = size if size >= 0 and size > available else max_buffer_size
                while available < needed and current_size < max_buffer_size:
                    try:
                        chunk = data_queue.get(timeout=0.05)
                    except Exception:
                        if download_complete.is_set():
                            break
                        continue

                    if chunk is None:  # End of stream
                        break

                    self.buffer.seek(0, 2)  # Seek to end
                    self.buffer.write(chunk)
                    current_size = self.buffer.tell()
                    available = current_size - self.buffer_pos

                # Read requested amount
                self.buffer.seek(self.buffer_pos)
                if size < 0:
                    result = self.buffer.read()
                    # Clear buffer
                    self.buffer.seek(0)
                    self.buffer.truncate(0)
                    self.buffer_pos = 0
                else:
                    result = self.buffer.read(size)
                    self.buffer_pos = self.buffer.tell()

                if download_error and not result:
                    raise download_error
                return result

            def close(self) -> None:
                """Close the stream."""

        # Extract using pipe mode for sequential reading
        reader = StreamingReader()
        with tarfile.open(fileobj=reader, mode="r|gz") as tar:
            for member in tar:
                tar.extract(member, path=target_dir, filter="data")

        # Wait for download to complete
        download_thread.join(timeout=10.0)
        if download_thread.is_alive():
            logger.warning("Download thread did not finish within timeout")

        if download_error:
            raise download_error

    finally:
        # Cleanup: drain queue if needed
        while not data_queue.empty():
            with suppress(Exception):
                data_queue.get_nowait()

    logger.info("Successfully downloaded and extracted from %s to %s", url, target_dir)


def needs_update(dest_path: Path, source_path: Path) -> bool:
    """Check if the destination path needs to be updated.

    Args:
        dest_path: Destination path.
        source_path: Source path.

    Returns:
        True if the destination path needs to be updated, False otherwise.

    """
    if not dest_path.exists():
        if dest_path.is_symlink() and not dest_path.resolve(strict=False).exists():
            return True
        return True

    if not dest_path.is_symlink():
        return True

    try:
        current_target = dest_path.readlink()
        expected_target = source_path.relative_to(dest_path.parent)

    except OSError:
        return True

    return current_target != expected_target

def symlink_file(source_path: Path, dest_path: Path) -> None:
    """Create a symlink from the source path to the destination path.

    Args:
        source_path: Source path.
        dest_path: Destination path.

    """
    if not needs_update(dest_path, source_path):
        return

    if dest_path.exists() or dest_path.is_symlink():
        with suppress(FileNotFoundError):
            dest_path.unlink()
    rel_target = os.path.relpath(source_path, dest_path.parent)
    dest_path.symlink_to(rel_target)


def _cleanup_orphaned_symlinks(dest: Path) -> None:
    """Remove symlinks in destination that point to non-existent files.

    Args:
        dest: Destination directory where symlinks are located.

    """
    if not dest.exists():
        return

    for symlink in dest.rglob("*"):
        if not symlink.is_symlink():
            continue

        try:
            target = symlink.readlink()
            # Resolve relative paths relative to symlink's parent
            if not target.is_absolute():
                target = (symlink.parent / target).resolve()
            else:
                target = target.resolve()

            # Remove if target doesn't exist
            if not target.exists():
                symlink.unlink()
                logger.debug("Removed orphaned symlink: %s", symlink)
        except (OSError, ValueError):
            # Broken symlink or error reading it - remove it
            try:
                symlink.unlink()
                logger.debug("Removed broken symlink: %s", symlink)
            except OSError:
                pass


def symlink_tree_parallel(
    src: Path, dest: Path, *, pattern: str | list[str] | None = None
) -> None:
    """Create a tree of symlinks from source to destination.

    Recursively creates symlinks for all files in the source directory tree,
    maintaining the directory structure in the destination.

    Args:
        src: Source directory path.
        dest: Destination directory path where symlinks will be created.
        pattern: Optional glob pattern(s) to filter files (e.g., "*.py", ["*.py", "*.txt"]).
            If None, all files are processed.

    Raises:
        ValueError: If destination path is a parent of source path.

    Examples:
        >>> symlink_tree_parallel(Path("/src"), Path("/dest"))
        >>> symlink_tree_parallel(Path("/src"), Path("/dest"), pattern="*.py")
        >>> symlink_tree_parallel(Path("/src"), Path("/dest"), pattern=["*.py", "*.txt"])

    """
    src = Path(src).resolve()
    dest = Path(dest).resolve()

    if dest in src.parents:
        msg = "Destination path cannot be a parent of the source path"
        raise ValueError(msg)

    # Clean up orphaned symlinks (pointing to files that no longer exist)
    _cleanup_orphaned_symlinks(dest)

    tasks = []
    matched_files: set[Path] = set()

    # Handle pattern(s)
    if pattern is None:
        # No pattern: get all files
        matched_files = {f for f in src.rglob("*") if f.is_file()}
    elif isinstance(pattern, str):
        # Single pattern
        matched_files = {f for f in src.rglob(pattern) if f.is_file()}
    else:
        # Multiple patterns: union of all matches
        matched_files = set()
        for pat in pattern:
            matched_files.update({f for f in src.rglob(pat) if f.is_file()})

    # Create tasks: for each matched file, determine destination path
    for src_file in matched_files:
        try:
            rel_path = src_file.relative_to(src)
        except ValueError:
            # File is not relative to src, skip it
            continue
        dest_file = dest / rel_path
        dest_dir = dest_file.parent
        tasks.append((src_file, dest_file, dest_dir))

    # Ensure all destination directories exist
    dest_dirs = {dest_dir for _, _, dest_dir in tasks}
    for dest_dir in dest_dirs:
        dest_dir.mkdir(parents=True, exist_ok=True)

    # Create symlinks sequentially
    for src_file, dest_file, _ in tasks:
        symlink_file(src_file, dest_file)
