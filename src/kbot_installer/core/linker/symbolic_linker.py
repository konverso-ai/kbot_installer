"""Symbolic linker implementation."""

import shutil
from collections.abc import Callable
from pathlib import Path

from kbot_installer.core.linker.linker_base import LinkerBase
from kbot_installer.core.utils import calculate_relative_path, ensure_directory


class SymbolicLinker(LinkerBase):
    """Concrete implementation for symbolic links.

    This class implements symbolic link creation and management with support for:
    - Relative and absolute links
    - Python extension handling (.py, .so)
    - Broken link detection and repair
    - Update mode for validating existing links

    Attributes:
        python_extensions: Tuple of Python file extensions to handle specially.

    """

    def __init__(
        self,
        base_path: Path,
        *,
        update_mode: bool = False,
        silent_mode: bool = False,
        interactive_callback: Callable[[str, str], bool] | None = None,
    ) -> None:
        """Initialize symbolic linker.

        Args:
            base_path: Base path for relative link calculations.
            update_mode: Enable update/validation mode.
            silent_mode: Suppress interactive prompts.
            interactive_callback: Function for yes/no prompts.

        """
        self.base_path = Path(base_path).resolve()
        self.update_mode = update_mode
        self.silent_mode = silent_mode
        self.interactive_callback = interactive_callback
        self.python_extensions = (".py", ".so")

    def link(self, src: Path, dst: Path) -> None:
        """Create a symbolic link from source to destination.

        Handles special cases for Python files (.py, .so) and validates
        existing links in update mode.

        Args:
            src: Source path.
            dst: Destination path.

        Raises:
            FileNotFoundError: If source doesn't exist.
            OSError: If link creation fails.

        """
        src = Path(src)
        dst = Path(dst)

        if not src.exists():
            return

        srcext = src.suffix
        dstext = dst.suffix

        # Handle Python extensions specially
        if srcext in self.python_extensions and dstext in self.python_extensions:
            self._link_python_file(src, dst)
        else:
            self._link_regular_file(src, dst)

    def _link_python_file(self, src: Path, dst: Path) -> None:
        """Link Python file handling .py and .so extensions."""
        dstroot = dst.parent / dst.stem

        for ext in self.python_extensions:
            dstname = dstroot.with_suffix(ext)
            if not dstname.exists():
                continue

            # Update mode: recreate if link points to wrong file
            if self.update_mode and dstname.is_symlink() and not src.samefile(dstname):
                if self._should_recreate(str(dstname)):
                    dstname.unlink()
                continue

            # File exists and is correct, no need to create link
            return

        # No existing file found, create link
        if dst.exists():
            return

        relative_path = calculate_relative_path(src, dst)
        dst.symlink_to(relative_path)

    def _link_regular_file(self, src: Path, dst: Path) -> None:
        """Link regular (non-Python) file."""
        if self.update_mode and dst.is_symlink():
            self._validate_existing_link(src, dst)

        if not dst.exists():
            relative_path = calculate_relative_path(src, dst)
            dst.symlink_to(relative_path)

    def _validate_existing_link(self, src: Path, dst: Path) -> None:
        """Validate and potentially fix existing link."""
        targetpath = Path(dst.readlink())
        # Get absolute path if relative
        if not targetpath.is_absolute():
            targetpath = self.base_path / targetpath
            targetpath = targetpath.resolve()

        if (not targetpath.exists() and self._should_remove(str(dst))) or (
            targetpath.exists()
            and not src.samefile(dst)
            and self._should_recreate(str(dst))
        ):
            dst.unlink()

    def link_absolute(self, src: Path, dst: Path) -> None:
        """Create an absolute symbolic link from source to destination.

        Args:
            src: Source path.
            dst: Destination path.

        Raises:
            FileNotFoundError: If source doesn't exist.
            OSError: If link creation fails.

        """
        src = Path(src).resolve()
        dst = Path(dst)

        if not dst.exists() and src.exists():
            dst.symlink_to(src)

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
        link_dirs = link_dirs or []
        ensure_directory(dst)

        if not src.exists():
            return

        for fullname in src.iterdir():
            dstname = dst / fullname.name

            # Handle files directly
            if fullname.is_file():
                self.link(fullname, dstname)
                continue

            # Handle directories
            if fullname.name in link_dirs:
                self.link(fullname, dstname)
                continue
            self.link_directory(fullname, dstname, link_dirs)

    def validate_links_in_dir(self, dir_path: Path) -> None:
        """Validate and repair links in a directory.

        Checks for broken links and optionally repairs or removes them
        based on update_mode and interactive_callback settings.

        Args:
            dir_path: Directory path to validate.

        """
        dir_path = Path(dir_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return

        for fullname in dir_path.iterdir():
            if not fullname.is_symlink():
                continue
            targetpath = Path(fullname.readlink())
            if not targetpath.is_absolute():
                targetpath = dir_path / targetpath
            if not targetpath.exists() and self._should_remove(str(fullname)):
                fullname.unlink()

    def link_product_files_to_dir(
        self,
        files: list[Path],
        dst: Path,
        link_dirs: list[str] | None = None,
        ignoredirs: list[str] | None = None,
    ) -> None:
        """Link product files to a destination directory.

        This method links files from a product collection, handling directories
        and files appropriately.

        Args:
            files: List of file paths to link.
            dst: Destination directory.
            link_dirs: List of directory names to link directly.
            ignoredirs: List of directory names to ignore.

        """
        if link_dirs is None:
            link_dirs = []
        if ignoredirs is None:
            ignoredirs = []

        ensure_directory(dst)

        # Check broken links in update mode
        if self.update_mode:
            self.validate_links_in_dir(dst)

        if not dst.exists():
            return

        dstdirs = {d.name for d in dst.iterdir() if d.is_dir()}

        for fullname in files:
            if not fullname.exists():
                continue

            fname = fullname.name
            dstname = dst / fname

            if fullname.is_dir():
                self._link_directory_item(
                    fullname, dstname, fname, link_dirs, dstdirs, ignoredirs
                )
            elif fullname.is_file():
                self.link(fullname, dstname)

        self._remove_unused_directories(dst, dstdirs, ignoredirs)

    def _link_directory_item(
        self,
        fullname: Path,
        dstname: Path,
        fname: str,
        link_dirs: list[str],
        dstdirs: set[str],
        ignoredirs: list[str],
    ) -> None:
        """Link a directory item from product files."""
        if fname in dstdirs:
            dstdirs.discard(fname)
        if fname in link_dirs:
            self.link(fullname, dstname)
            return

        # Recursively link directory contents
        subfiles = [p for p in fullname.iterdir() if p.exists()]
        if not subfiles:
            return
        self.link_product_files_to_dir(subfiles, dstname, link_dirs, ignoredirs)

    def _remove_unused_directories(
        self,
        dst: Path,
        dstdirs: set[str],
        ignoredirs: list[str],
    ) -> None:
        """Remove unused directories from destination."""
        for dstdir in dstdirs:
            # Skip special directories and ignored directories
            if dstdir.startswith("__") or dstdir in ignoredirs:
                continue

            unused_dir = dst / dstdir
            # Skip symlink directories (warning only, no action)
            if unused_dir.is_symlink():
                continue

            # Remove unused regular directory
            if unused_dir.is_dir() and self._should_remove_unused_dir(str(unused_dir)):
                shutil.rmtree(unused_dir)

    def _should_recreate(self, link_path: str) -> bool:
        """Check if a link should be recreated.

        Args:
            link_path: Path to the link.

        Returns:
            True if link should be recreated.

        """
        if self.silent_mode:
            return True
        if self.interactive_callback:
            return self.interactive_callback(
                f"Wrong link '{link_path}'. Recreate it? [yes]: ", "yes"
            )
        return True

    def _should_remove(self, link_path: str) -> bool:
        """Check if a broken link should be removed.

        Args:
            link_path: Path to the link.

        Returns:
            True if link should be removed.

        """
        if self.silent_mode:
            return True
        if self.interactive_callback:
            return self.interactive_callback(
                f"Broken link '{link_path}'. Remove it? [yes]: ", "yes"
            )
        return True

    def _should_remove_unused_dir(self, dir_path: str) -> bool:
        """Check if an unused directory should be removed.

        Args:
            dir_path: Path to the directory.

        Returns:
            True if directory should be removed.

        """
        if self.silent_mode:
            return True
        if self.interactive_callback:
            return self.interactive_callback(
                f"Not used directory '{dir_path}'. Remove it? [yes]: ", "yes"
            )
        return True
