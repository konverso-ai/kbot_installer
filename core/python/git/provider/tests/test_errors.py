"""Tests for errors module."""

import pytest

from git.provider.errors import ProviderError


class TestProviderError:
    """Test cases for ProviderError class."""

    def test_inherits_from_exception(self) -> None:
        """Test that ProviderError inherits from Exception."""
        assert issubclass(ProviderError, Exception)

    def test_can_be_raised(self) -> None:
        """Test that ProviderError can be raised."""
        error_message = "Test error"
        with pytest.raises(ProviderError):
            raise ProviderError(error_message)

    def test_can_be_raised_with_message(self) -> None:
        """Test that ProviderError can be raised with a message."""
        message = "Test error message"
        with pytest.raises(ProviderError) as exc_info:
            raise ProviderError(message)
        assert str(exc_info.value) == message
