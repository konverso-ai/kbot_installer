"""Utility functions for kbot-installer."""

import logging
import os
import tarfile
import tempfile
from collections.abc import Iterator
from pathlib import Path
from queue import Queue
from tempfile import SpooledTemporaryFile
from threading import Thread

import httpx

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


def optimized_download_and_extract_ter(
    url: str, target_dir: Path, auth_obj: object | None = None
) -> None:
    """Télécharge et extrait simultanément un tar.gz.

    Utilise le mode pipe de tarfile pour éviter les seeks.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    with httpx.stream("GET", url, timeout=60.0, auth=auth_obj) as response:
        response.raise_for_status()

        # Créer un itérateur de chunks
        def chunk_iterator() -> Iterator[bytes]:
            yield from response.iter_bytes(chunk_size=16 * 1024 * 1024)

        # Wrapper pour rendre l'itérateur compatible avec tarfile
        class StreamWrapper:
            def __init__(self, iterator: Iterator[bytes]) -> None:
                self.iterator = iterator
                self.buffer = b""

            def read(self, size: int = -1) -> bytes:
                while size < 0 or len(self.buffer) < size:
                    try:
                        self.buffer += next(self.iterator)
                    except StopIteration:
                        break

                if size < 0:
                    result = self.buffer
                    self.buffer = b""
                else:
                    result = self.buffer[:size]
                    self.buffer = self.buffer[size:]

                return result

        # Extraire directement depuis le stream
        # Le mode "|gz" (pipe) permet de lire séquentiellement sans seek
        stream = StreamWrapper(chunk_iterator())
        with tarfile.open(fileobj=stream, mode="r|gz") as tar:
            for member in tar:
                tar.extract(member, path=target_dir, filter="data")

    logger.info("Successfully downloaded and extracted from %s to %s", url, target_dir)
