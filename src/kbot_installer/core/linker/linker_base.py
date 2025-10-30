"""Base class for linkers."""

from abc import ABC, abstractmethod
from pathlib import Path


class LinkerBase(ABC):
    """Abstract base class for creating and managing links.

    This class provides the interface for different link implementations.
    Concrete implementations should handle specific link types (symbolic links,
    hard links, etc.) and their management.

    Attributes:
        base_path: Base path used for calculating relative link paths.
        update_mode: If True, validates and repairs existing links.
        silent_mode: If True, suppresses interactive prompts.
        interactive_callback: Callback function for interactive prompts.
            Should accept (question: str, default: str) -> bool.

    """

    @abstractmethod
    def link(self, src: Path, dst: Path) -> None:
        """Create a link from source to destination.

        Args:
            src: Source path.
            dst: Destination path.

        Raises:
            FileNotFoundError: If source doesn't exist.
            OSError: If link creation fails.

        """

    @abstractmethod
    def link_absolute(self, src: Path, dst: Path) -> None:
        """Create an absolute link from source to destination.

        Args:
            src: Source path.
            dst: Destination path.

        Raises:
            FileNotFoundError: If source doesn't exist.
            OSError: If link creation fails.

        """

    @abstractmethod
    def link_directory(
        self, src: Path, dst: Path, link_dirs: list[str] | None = None
    ) -> None:
        """Recursively link directory contents.

        Args:
            src: Source directory path.
            dst: Destination directory path.
            link_dirs: List of directory names to link directly (not recursively).

        Raises:
            FileNotFoundError: If source doesn't exist.
            OSError: If link creation fails.

        """

    @abstractmethod
    def validate_links_in_dir(self, dir_path: Path) -> None:
        """Validate and repair links in a directory.

        In update_mode, this method checks for broken links and optionally
        repairs or removes them.

        Args:
            dir_path: Directory path to validate.

        """
