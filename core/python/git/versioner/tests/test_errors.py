"""Tests for versioner.errors module."""

import pytest

from git.versioner.errors import VersionerError


class TestVersionerError:
    """Test cases for VersionerError."""

    def test_inherits_from_exception(self) -> None:
        """Test that VersionerError inherits from Exception."""
        assert issubclass(VersionerError, Exception)

    def test_can_be_raised(self) -> None:
        """Test that VersionerError can be raised."""
        error_message = "Test error"
        with pytest.raises(VersionerError):
            raise VersionerError(error_message)

    def test_can_be_raised_with_message(self) -> None:
        """Test that VersionerError can be raised with a message."""
        message = "Test error message"
        with pytest.raises(VersionerError) as exc_info:
            raise VersionerError(message)
        assert str(exc_info.value) == message
