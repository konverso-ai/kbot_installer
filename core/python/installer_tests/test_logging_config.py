"""Tests for logging_config module."""

import logging
from pathlib import Path

from installer_support.logging_config import setup_logging


class TestSetupLoggingQuietsThirdParty:
    """Test cases ensuring noisy third-party loggers are silenced."""

    def test_setup_logging_from_file_quiets_azure(self) -> None:
        """Test that loading logging.conf caps the azure logger at WARNING."""
        logging.getLogger("azure").setLevel(logging.NOTSET)

        setup_logging()

        assert logging.getLogger("azure").getEffectiveLevel() == logging.WARNING

    def test_setup_logging_fallback_quiets_azure(self, tmp_path: Path) -> None:
        """Test that the basicConfig fallback also caps the azure logger."""
        logging.getLogger("azure").setLevel(logging.NOTSET)
        missing_config = tmp_path / "missing_logging.conf"

        setup_logging(config_path=missing_config)

        assert logging.getLogger("azure").getEffectiveLevel() == logging.WARNING
