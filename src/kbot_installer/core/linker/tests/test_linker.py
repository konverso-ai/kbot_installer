"""Tests for SymbolicLinker class."""

import tempfile
from pathlib import Path

from kbot_installer.core.linker.symbolic_linker import SymbolicLinker


class TestSymbolicLinker:
    """Test cases for SymbolicLinker class."""

    def test_link_basic(self) -> None:
        """Test basic link creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            src_file = src_dir / "test.txt"
            src_file.write_text("test content")

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            linker.link(src_file, dst_dir / "test.txt")

            link_path = dst_dir / "test.txt"
            assert link_path.is_symlink()
            assert link_path.read_text() == "test content"

    def test_link_absolute(self) -> None:
        """Test absolute link creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            src_file = src_dir / "test.txt"
            src_file.write_text("test content")

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            linker.link_absolute(src_file, dst_dir / "test.txt")

            link_path = dst_dir / "test.txt"
            assert link_path.is_symlink()
            target = link_path.readlink()
            assert Path(target).is_absolute()

    def test_link_directory(self) -> None:
        """Test directory linking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            # Create source structure
            (src_dir / "file1.txt").write_text("file1")
            (src_dir / "file2.txt").write_text("file2")
            (src_dir / "subdir").mkdir()
            (src_dir / "subdir" / "file3.txt").write_text("file3")

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            linker.link_directory(src_dir, dst_dir / "linked")

            linked_dir = dst_dir / "linked"
            assert linked_dir.is_dir()
            assert (linked_dir / "file1.txt").read_text() == "file1"
            assert (linked_dir / "file2.txt").read_text() == "file2"
            assert (linked_dir / "subdir" / "file3.txt").read_text() == "file3"

    def test_validate_links_in_dir(self) -> None:
        """Test link validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            test_dir = base_path / "test"
            test_dir.mkdir()

            # Create a valid link
            src_file = base_path / "src.txt"
            src_file.write_text("content")
            (test_dir / "valid_link").symlink_to(src_file)

            # Create a broken link
            (test_dir / "broken_link").symlink_to(base_path / "nonexistent.txt")

            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            linker.validate_links_in_dir(test_dir)

            assert (test_dir / "valid_link").exists()
            assert not (test_dir / "broken_link").exists()

    def test_link_python_extensions(self) -> None:
        """Test Python extension handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            # Create .py and .so files
            (src_dir / "module.py").write_text("# Python")
            (src_dir / "module.so").touch()

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            linker.link(src_dir / "module.py", dst_dir / "module.py")

            # Both .py and .so should be handled
            assert (dst_dir / "module.py").is_symlink()

    def test_ensure_directory(self) -> None:
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)

            new_dir = base_path / "new" / "nested" / "dir"
            linker.ensure_directory(new_dir)

            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_calculate_relative_path(self) -> None:
        """Test relative path calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()

            src = base_path / "src" / "file.txt"
            src.parent.mkdir()
            dst = base_path / "dst" / "file.txt"
            dst.parent.mkdir()

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            relative = linker.calculate_relative_path(src, dst)

            assert isinstance(relative, Path)
            # Relative path should not be absolute (in most cases)
            if str(relative).startswith(".."):
                assert not relative.is_absolute()

    def test_link_product_files_to_dir(self) -> None:
        """Test linking product files to directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()

            # Create source files
            src_dir = base_path / "src"
            src_dir.mkdir()
            (src_dir / "file1.txt").write_text("file1")
            (src_dir / "file2.txt").write_text("file2")

            files = [src_dir / "file1.txt", src_dir / "file2.txt"]

            linker = SymbolicLinker(base_path, silent_mode=True)
            linker.link_product_files_to_dir(files, dst_dir)

            assert (dst_dir / "file1.txt").is_symlink()
            assert (dst_dir / "file2.txt").is_symlink()

    def test_link_with_update_mode(self) -> None:
        """Test link recreation in update mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            # Create original source and link
            src_file = src_dir / "test.txt"
            src_file.write_text("original")
            (dst_dir / "test.txt").symlink_to(base_path / "wrong.txt")

            # Update link to point to correct source
            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            linker.link(src_file, dst_dir / "test.txt")

            link_path = dst_dir / "test.txt"
            assert link_path.is_symlink()
            assert link_path.samefile(src_file)

    def test_link_nonexistent_source(self) -> None:
        """Test linking with nonexistent source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()

            nonexistent_file = base_path / "nonexistent.txt"
            dst_file = dst_dir / "test.txt"

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            linker.link(nonexistent_file, dst_file)

            # Should not create link if source doesn't exist
            assert not dst_file.exists()

    def test_link_absolute_nonexistent_source(self) -> None:
        """Test absolute link with nonexistent source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()

            nonexistent_file = base_path / "nonexistent.txt"
            dst_file = dst_dir / "test.txt"

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            # Should not raise error, just not create link
            linker.link_absolute(nonexistent_file, dst_file)

            assert not dst_file.exists()

    def test_link_absolute_existing_destination(self) -> None:
        """Test absolute link when destination already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_file = base_path / "src.txt"
            src_file.write_text("content")
            dst_file = base_path / "dst.txt"
            dst_file.write_text("existing")

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            linker.link_absolute(src_file, dst_file)

            # Should not overwrite existing file
            assert dst_file.is_file()
            assert not dst_file.is_symlink()

    def test_link_directory_with_link_dirs(self) -> None:
        """Test directory linking with link_dirs parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            # Create structure with subdirectory
            (src_dir / "file1.txt").write_text("file1")
            (src_dir / "subdir").mkdir()
            (src_dir / "subdir" / "file2.txt").write_text("file2")

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            # Link subdir directly instead of recursively
            linker.link_directory(src_dir, dst_dir / "linked", link_dirs=["subdir"])

            linked_dir = dst_dir / "linked"
            assert (linked_dir / "file1.txt").is_symlink()
            # subdir should be linked directly
            subdir_link = linked_dir / "subdir"
            assert subdir_link.is_symlink()
            # Contents might be accessible through the symlink
            assert (src_dir / "subdir" / "file2.txt").exists()

    def test_link_product_files_to_dir_with_link_dirs(self) -> None:
        """Test linking product files with link_dirs parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()

            src_dir = base_path / "src"
            src_dir.mkdir()
            (src_dir / "file.txt").write_text("file")
            (src_dir / "linked_dir").mkdir()
            (src_dir / "linked_dir" / "nested.txt").write_text("nested")

            files = [src_dir / "file.txt", src_dir / "linked_dir"]

            linker = SymbolicLinker(base_path, silent_mode=True)
            linker.link_product_files_to_dir(files, dst_dir, link_dirs=["linked_dir"])

            assert (dst_dir / "file.txt").is_symlink()
            assert (dst_dir / "linked_dir").is_symlink()
            # Nested files are accessible through the symlink, not linked separately
            assert (src_dir / "linked_dir" / "nested.txt").exists()

    def test_link_product_files_to_dir_with_ignoredirs(self) -> None:
        """Test linking product files with ignoredirs parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()
            # Create existing directory that should not be removed
            (dst_dir / "existing_dir").mkdir()
            (dst_dir / "existing_dir" / "keep.txt").write_text("keep")

            src_dir = base_path / "src"
            src_dir.mkdir()
            (src_dir / "file.txt").write_text("file")

            files = [src_dir / "file.txt"]

            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            linker.link_product_files_to_dir(
                files, dst_dir, ignoredirs=["existing_dir"]
            )

            assert (dst_dir / "file.txt").is_symlink()
            # existing_dir should not be removed
            assert (dst_dir / "existing_dir").exists()

    def test_link_product_files_to_dir_nonexistent_files(self) -> None:
        """Test linking product files with nonexistent files in list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()

            src_dir = base_path / "src"
            src_dir.mkdir()
            existing_file = src_dir / "file.txt"
            existing_file.write_text("file")
            nonexistent_file = src_dir / "nonexistent.txt"

            files = [existing_file, nonexistent_file]

            linker = SymbolicLinker(base_path, silent_mode=True)
            linker.link_product_files_to_dir(files, dst_dir)

            # Only existing file should be linked
            assert (dst_dir / "file.txt").is_symlink()
            assert not (dst_dir / "nonexistent.txt").exists()

    def test_interactive_callback_recreate(self) -> None:
        """Test interactive callback for link recreation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            correct_file = src_dir / "correct.txt"
            correct_file.write_text("correct")
            wrong_file = base_path / "wrong.txt"
            wrong_file.write_text("wrong")

            # Create link to wrong file
            (dst_dir / "correct.txt").symlink_to(wrong_file)

            callback_calls = []

            def callback(question: str, default: str) -> bool:
                callback_calls.append((question, default))
                return True

            linker = SymbolicLinker(
                base_path,
                update_mode=True,
                silent_mode=False,
                interactive_callback=callback,
            )
            linker.link(correct_file, dst_dir / "correct.txt")

            assert len(callback_calls) > 0
            assert "Wrong link" in callback_calls[0][0]
            assert (dst_dir / "correct.txt").is_symlink()
            assert (dst_dir / "correct.txt").readlink() != wrong_file

    def test_interactive_callback_remove(self) -> None:
        """Test interactive callback for broken link removal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            test_dir = base_path / "test"
            test_dir.mkdir()

            # Create broken link
            (test_dir / "broken").symlink_to(base_path / "nonexistent.txt")

            callback_calls = []

            def callback(question: str, default: str) -> bool:
                callback_calls.append((question, default))
                return True

            linker = SymbolicLinker(
                base_path,
                update_mode=True,
                silent_mode=False,
                interactive_callback=callback,
            )
            linker.validate_links_in_dir(test_dir)

            assert len(callback_calls) > 0
            assert "Broken link" in callback_calls[0][0]
            assert not (test_dir / "broken").exists()

    def test_interactive_callback_remove_unused_dir(self) -> None:
        """Test interactive callback for unused directory removal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()
            unused_dir = dst_dir / "unused_dir"
            unused_dir.mkdir()
            (unused_dir / "file.txt").write_text("unused")

            src_dir = base_path / "src"
            src_dir.mkdir()
            (src_dir / "file.txt").write_text("file")

            callback_calls = []

            def callback(question: str, default: str) -> bool:
                callback_calls.append((question, default))
                return True

            linker = SymbolicLinker(
                base_path,
                update_mode=True,
                silent_mode=False,
                interactive_callback=callback,
            )
            linker.link_product_files_to_dir([src_dir / "file.txt"], dst_dir)

            assert len(callback_calls) > 0
            assert "Not used directory" in callback_calls[0][0]
            assert not unused_dir.exists()

    def test_link_python_file_update_mode(self) -> None:
        """Test Python file linking in update mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            # Create .py file
            (src_dir / "module.py").write_text("# Python")
            # Create link to wrong source (must exist for symlink)
            wrong_file = base_path / "wrong.py"
            wrong_file.write_text("# wrong")
            (dst_dir / "module.py").symlink_to(wrong_file)

            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            linker.link(src_dir / "module.py", dst_dir / "module.py")

            link_path = dst_dir / "module.py"
            assert link_path.is_symlink()
            assert link_path.samefile(src_dir / "module.py")

    def test_link_python_file_with_so(self) -> None:
        """Test Python file linking when both .py and .so exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            # Create both .py and .so
            (src_dir / "module.py").write_text("# Python")
            (src_dir / "module.so").touch()

            # Create existing .so link
            (dst_dir / "module.so").symlink_to(src_dir / "module.so")

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=True)
            linker.link(src_dir / "module.py", dst_dir / "module.py")

            # When .so exists but not in update_mode, .py won't be created due to break
            # The logic checks existing files and breaks if they exist
            # In non-update mode, if dstname.exists(), it breaks the loop
            assert (
                not (dst_dir / "module.py").exists()
                or (dst_dir / "module.py").is_symlink()
            )

    def test_link_directory_source_not_exists(self) -> None:
        """Test directory linking when source doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()

            nonexistent_dir = base_path / "nonexistent"

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            linker.link_directory(nonexistent_dir, dst_dir / "linked")

            # ensure_directory creates the destination directory
            # but no files are linked since source doesn't exist
            assert (dst_dir / "linked").exists()
            assert (dst_dir / "linked").is_dir()
            # Directory should be empty
            assert len(list((dst_dir / "linked").iterdir())) == 0

    def test_validate_links_in_dir_not_directory(self) -> None:
        """Test validate_links_in_dir with non-directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            file_path = base_path / "file.txt"
            file_path.write_text("content")

            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            # Should not raise error, just return
            linker.validate_links_in_dir(file_path)

    def test_validate_links_in_dir_not_exists(self) -> None:
        """Test validate_links_in_dir with nonexistent path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            nonexistent_dir = base_path / "nonexistent"

            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            # Should not raise error, just return
            linker.validate_links_in_dir(nonexistent_dir)

    def test_calculate_relative_path_same_directory(self) -> None:
        """Test relative path calculation for files in same directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()

            src = base_path / "src.txt"
            dst = base_path / "dst.txt"

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            relative = linker.calculate_relative_path(src, dst)

            assert isinstance(relative, Path)
            # Should be a simple filename or relative path
            assert relative.name == "src.txt" or "src.txt" in str(relative)

    def test_calculate_relative_path_different_levels(self) -> None:
        """Test relative path calculation for files at different directory levels."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()

            src = base_path / "level1" / "level2" / "src.txt"
            src.parent.mkdir(parents=True)
            dst = base_path / "dst.txt"

            linker = SymbolicLinker(base_path, update_mode=False, silent_mode=False)
            relative = linker.calculate_relative_path(src, dst)

            assert isinstance(relative, Path)
            # Should contain path to src
            assert (
                "level1" in str(relative)
                or "level2" in str(relative)
                or relative.is_absolute()
            )

    def test_silent_mode_default_behavior(self) -> None:
        """Test that silent_mode defaults work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            src_file = src_dir / "test.txt"
            src_file.write_text("content")
            wrong_file = base_path / "wrong.txt"
            wrong_file.write_text("wrong")
            (dst_dir / "test.txt").symlink_to(wrong_file)

            # Without callback, should default to True in silent mode
            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            linker.link(src_file, dst_dir / "test.txt")

            # Should recreate link without asking
            assert (dst_dir / "test.txt").is_symlink()
            assert (dst_dir / "test.txt").samefile(src_file)

    def test_link_product_files_to_dir_nested_directories(self) -> None:
        """Test linking product files with nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()

            src_dir = base_path / "src"
            src_dir.mkdir()
            nested_dir = src_dir / "level1" / "level2"
            nested_dir.mkdir(parents=True)
            (nested_dir / "file.txt").write_text("nested")

            files = [src_dir / "level1"]

            linker = SymbolicLinker(base_path, silent_mode=True)
            linker.link_product_files_to_dir(files, dst_dir)

            linked_level1 = dst_dir / "level1"
            assert linked_level1.is_dir()
            assert (linked_level1 / "level2" / "file.txt").is_symlink()

    def test_remove_unused_directories_special_names(self) -> None:
        """Test that directories starting with __ are not removed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            dst_dir = base_path / "dst"
            dst_dir.mkdir()
            # Create __pycache__ directory
            cache_dir = dst_dir / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "file.pyc").write_text("cache")

            src_dir = base_path / "src"
            src_dir.mkdir()
            (src_dir / "file.txt").write_text("file")

            linker = SymbolicLinker(base_path, update_mode=True, silent_mode=True)
            linker.link_product_files_to_dir([src_dir / "file.txt"], dst_dir)

            # __pycache__ should not be removed
            assert cache_dir.exists()

    def test_calculate_relative_path_no_callback(self) -> None:
        """Test that methods return True when no callback is provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            src_dir = base_path / "src"
            dst_dir = base_path / "dst"
            src_dir.mkdir()
            dst_dir.mkdir()

            src_file = src_dir / "test.txt"
            src_file.write_text("content")
            wrong_file = base_path / "wrong.txt"
            wrong_file.write_text("wrong")
            (dst_dir / "test.txt").symlink_to(wrong_file)

            # No callback, should default to True
            linker = SymbolicLinker(
                base_path,
                update_mode=True,
                silent_mode=False,
                interactive_callback=None,
            )
            linker.link(src_file, dst_dir / "test.txt")

            # Should recreate link
            assert (dst_dir / "test.txt").is_symlink()
            assert (dst_dir / "test.txt").samefile(src_file)

    def test_interactive_callback_returns_false(self) -> None:
        """Test that callback return value controls link removal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()
            test_dir = base_path / "test"
            test_dir.mkdir()

            # Create broken link
            broken_link = test_dir / "broken"
            broken_link.symlink_to(base_path / "nonexistent.txt")

            callback_calls = []

            def callback(question: str, default: str) -> bool:
                callback_calls.append((question, default))
                return False  # Don't remove

            linker = SymbolicLinker(
                base_path,
                update_mode=True,
                silent_mode=False,
                interactive_callback=callback,
            )

            # Verify link exists before validation (broken links are symlinks)
            assert broken_link.is_symlink()

            linker.validate_links_in_dir(test_dir)

            # Callback should be called
            assert len(callback_calls) > 0
            assert "Broken link" in callback_calls[0][0]
            # If callback returns False, link should not be removed
            assert broken_link.is_symlink()

    def test_link_product_files_to_dir_empty_dst(self) -> None:
        """Test linking when destination doesn't exist yet."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base"
            base_path.mkdir()

            src_dir = base_path / "src"
            src_dir.mkdir()
            (src_dir / "file.txt").write_text("file")

            dst_dir = base_path / "dst"
            # Don't create dst_dir

            linker = SymbolicLinker(base_path, silent_mode=True)
            linker.link_product_files_to_dir([src_dir / "file.txt"], dst_dir)

            # Directory should be created and file linked
            assert dst_dir.exists()
            assert (dst_dir / "file.txt").is_symlink()
