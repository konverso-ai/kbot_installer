"""Extended tests for SelectorProvider."""

from unittest.mock import MagicMock, patch

import pytest

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.selector_provider import SelectorProvider


class TestSelectorProviderExtended:
    """Extended test cases for SelectorProvider."""

    def test_init_with_empty_providers(self) -> None:
        """Test SelectorProvider initialization with empty providers list."""
        selector = SelectorProvider(providers=[])

        assert selector.providers == []

    def test_clone_with_empty_providers_raises(self) -> None:
        """Test clone with no providers raises immediately with empty details."""
        selector = SelectorProvider(providers=[])

        with pytest.raises(ProviderError, match=r"All providers failed to clone repository 'test-repo':\n$"):
            selector.clone_and_checkout("test-repo", "/tmp/test")

    def test_remote_exists_with_empty_providers(self) -> None:
        """Test remote_exists with no providers returns False."""
        selector = SelectorProvider(providers=[])

        assert selector.remote_exists("test-repo") is False

    def test_name_not_updated_when_all_providers_fail(self) -> None:
        """Test that self.name stays unset when every provider fails."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_provider.clone_and_checkout.side_effect = ProviderError("boom")
        selector = SelectorProvider([mock_provider])

        with pytest.raises(ProviderError):
            selector.clone_and_checkout("test-repo", "/tmp/test")

        assert selector.name == ""

    def test_name_update_ignores_get_name_errors(self) -> None:
        """Test that a failing get_name() does not break a successful clone."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_provider.get_name.side_effect = RuntimeError("boom")
        selector = SelectorProvider([mock_provider])

        # Should not raise even though get_name() fails internally.
        selector.clone_and_checkout("test-repo", "/tmp/test", branch="main")

        assert selector.name == ""

    def test_clone_logs_info_when_not_quiet(self) -> None:
        """Test that a successful clone logs at info level by default."""
        mock_provider = MagicMock(spec=ProviderBase)
        selector = SelectorProvider([mock_provider], quiet=False)

        with patch("git.provider.selector_provider.log") as mock_log:
            selector.clone_and_checkout("test-repo", "/tmp/test", branch="main")

            mock_log.info.assert_called_once()
            mock_log.debug.assert_not_called()

    def test_clone_logs_debug_when_quiet(self) -> None:
        """Test that a successful clone logs at debug level when quiet=True."""
        mock_provider = MagicMock(spec=ProviderBase)
        selector = SelectorProvider([mock_provider], quiet=True)

        with patch("git.provider.selector_provider.log") as mock_log:
            selector.clone_and_checkout("test-repo", "/tmp/test", branch="main")

            mock_log.debug.assert_called_once()
            mock_log.info.assert_not_called()

    def test_clone_error_details_include_each_provider(self) -> None:
        """Test that the aggregated error message lists every provider's failure."""
        mock_storage = MagicMock(spec=ProviderBase)
        mock_github = MagicMock(spec=ProviderBase)
        mock_storage.clone_and_checkout.side_effect = ProviderError("storage down")
        mock_github.clone_and_checkout.side_effect = ProviderError("github down")
        selector = SelectorProvider([mock_storage, mock_github])

        with pytest.raises(ProviderError) as exc_info:
            selector.clone_and_checkout("test-repo", "/tmp/test", branch="main")

        error_msg = str(exc_info.value)
        assert "storage down" in error_msg
        assert "github down" in error_msg
