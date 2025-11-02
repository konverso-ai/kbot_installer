"""Logging configuration module for kbot_installer.

This module provides utilities to configure logging with a detailed format
that includes level, package, class/method/function, line number, and message.
"""

import inspect
import logging
import logging.config
from pathlib import Path


class DetailedFormatter(logging.Formatter):
    """Custom formatter that includes class name in log output.

    This formatter extends the standard logging.Formatter to include
    class name information in the log format.

    Format: levelname package.classname.funcName(lineno): message
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with class name if available.

        Args:
            record: Log record to format.

        Returns:
            Formatted log message with class name included.

        """
        classname = self._extract_class_name(record)
        class_part = f"{classname}." if classname else ""

        log_format = (
            f"{record.levelname} {record.name}.{class_part}{record.funcName}"
            f"({record.lineno}): {record.getMessage()}"
        )

        # Handle exception info if present
        if record.exc_info:
            log_format += "\n" + self.formatException(record.exc_info)

        return log_format

    def _extract_class_name(self, record: logging.LogRecord) -> str:
        """Extract class name from the frame where logging was called.

        Args:
            record: Log record containing frame information.

        Returns:
            Class name if found, empty string otherwise.

        """
        try:
            frame = self._find_logging_frame(record)
            if frame and "self" in frame.f_locals:
                instance = frame.f_locals["self"]
                if hasattr(instance, "__class__"):
                    return instance.__class__.__name__
        except Exception as e:
            # Silently ignore exceptions during class name extraction
            # to avoid breaking logging functionality
            logging.getLogger(__name__).debug("Failed to extract class name: %s", e)
        return ""

    def _find_logging_frame(self, record: logging.LogRecord) -> object | None:
        """Find the frame where the logging call was made.

        Args:
            record: Log record containing pathname information.

        Returns:
            Frame object if found, None otherwise.

        """
        frame = None
        try:
            for frame_info in inspect.stack():
                frame_filename = frame_info.filename

                # Skip frames related to logging internals or this formatter
                if self._should_skip_frame(frame_filename):
                    continue

                # Check if this frame matches the record location
                if frame_filename == record.pathname:
                    frame = frame_info.frame
                    break
        finally:
            # Clean up frame reference if needed
            pass

        return frame

    def _should_skip_frame(self, filename: str) -> bool:
        """Check if a frame should be skipped.

        Args:
            filename: Frame filename to check.

        Returns:
            True if frame should be skipped, False otherwise.

        """
        if "logging_config.py" in filename:
            return True
        return "/logging/__init__.py" in filename


def setup_logging(config_path: Path | None = None) -> None:
    """Set up logging configuration from file.

    Args:
        config_path: Path to logging configuration file.
                    If None, uses logging.conf in project root.

    """
    if config_path is None:
        # Find project root (where logging.conf should be)
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "logging.conf"

    if not config_path.exists():
        # Fallback to basic configuration with detailed format
        handler = logging.StreamHandler()
        handler.setFormatter(DetailedFormatter())
        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler],
        )
        return

    # Load configuration from file
    logging.config.fileConfig(
        str(config_path),
        disable_existing_loggers=False,
    )

    # Replace all formatters with our custom DetailedFormatter
    detailed_formatter = DetailedFormatter()
    for logger in [logging.root] + [
        logging.getLogger(name) for name in logging.Logger.manager.loggerDict
    ]:
        for handler in logger.handlers:
            handler.setFormatter(detailed_formatter)
