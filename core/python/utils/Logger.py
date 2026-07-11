"""KBot logger."""

import datetime
import io
import logging
import os
import sys
import time
import traceback
import warnings
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING, cast

from pythonjsonlogger.json import JsonFormatter
from typing_extensions import override

if TYPE_CHECKING:
    from errors import ErrorCode

try:
    glevel = int(os.environ["KBOTDEBUG"])
except (KeyError, ValueError):
    glevel = 1

FINE = 9
FINEST = 8

levels = {
    0: logging.CRITICAL,
    1: logging.WARN,
    2: logging.INFO,
    3: logging.DEBUG,
    4: FINE,
    5: FINEST,
}

name_to_level = {
    "error": 0,
    "warning": 1,
    "info": 2,
    "debug": 3,
    "fine": 4,
    "finest": 5,
}


def NormalizeLevel(level: int) -> int:
    """Normalize level value"""
    if level < 0:
        level = 0
    elif level > 5:
        level = 5
    return level


glevel = NormalizeLevel(glevel)

# Any stack frame living in this file is a logging wrapper, not a real call
# site: findCaller() below skips them so records always report the actual
# caller regardless of how many KbotLogger/KbotPackageLogger layers are crossed.       vv v v v v v v vvvvvvvvvvvvvvvvvvvvvvvv
_srcfile = os.path.normcase(NormalizeLevel.__code__.co_filename)


class KbotLogger(logging.Logger):
    """Logger for Kbot"""

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

        # key: a package name
        # value: a KbotPackageLogger object
        self.__packages = {}

        # key: a package name ('all' is the catch-all bucket)
        # value: the minimum level enabled for that package
        self.__filters: dict[str, int] = {}

    @property
    def packages(self):
        """Returns an iterator that contains all the registered package names"""
        return self.__packages.keys()

    @override
    def setLevel(self, level):
        self.addPackage("all", level)

    def fine(self, msg, *args, **kwargs):
        """FINE debug level"""
        self._log(FINE, msg, args, **kwargs)

    def finest(self, msg, *args, **kwargs):
        """FINEST debug level"""
        self._log(FINEST, msg, args, **kwargs)

    @override
    def debug(self, msg, *args, **kwargs):
        self._log(logging.DEBUG, msg, args, **kwargs)

    @override
    def info(self, msg, *args, **kwargs):
        self._log(logging.INFO, msg, args, **kwargs)

    @override
    def warning(self, msg, *args, **kwargs):
        self._log(logging.WARNING, msg, args, **kwargs)

    @override
    def warn(self, msg, *args, **kwargs):
        warnings.warn(
            "The 'warn' method is deprecated, use 'warning' instead",
            DeprecationWarning,
            2,
        )
        self.warning(msg, *args, **kwargs)

    @override
    def error(self, msg, *args, **kwargs):
        self._log(logging.ERROR, msg, args, **kwargs)

    @override
    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    @override
    def critical(self, msg, *args, **kwargs):
        self._log(logging.CRITICAL, msg, args, **kwargs)

    @override
    def isEnabledFor(self, level, package: str = "all") -> bool:
        if package not in self.__filters:
            package = "all"
        return level >= self.__filters[package]

    @override
    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        stacklevel=1,
        package="",
    ):
        if not self.isEnabledFor(level, package or "all"):
            return

        merged_extra = dict(extra or {})
        merged_extra["package"] = package
        super()._log(
            level,
            msg,
            args,
            exc_info=exc_info,
            extra=merged_extra,
            stack_info=stack_info,
            stacklevel=stacklevel,
        )

    @override
    def findCaller(self, stack_info=False, stacklevel=1):
        # stdlib's Logger._log() already traps the ValueError this raises when
        # the stack isn't deep enough (e.g. some IronPython versions).
        f = sys._getframe(4)
        # f's frame and everything below it up to here belongs to this module
        # (KbotLogger/KbotPackageLogger wrapper layers), regardless of how many
        # of them were crossed: skip them all to reach the real call site.
        while hasattr(f, "f_code"):
            co = f.f_code
            if os.path.normcase(co.co_filename) == _srcfile:
                f = f.f_back
                continue
            sinfo = None
            if stack_info:
                sio = io.StringIO()
                sio.write("Stack (most recent call last):\n")
                traceback.print_stack(f, file=sio)
                sinfo = sio.getvalue()
                if sinfo[-1] == "\n":
                    sinfo = sinfo[:-1]
                sio.close()
            return co.co_filename, f.f_lineno, co.co_name, sinfo
        return "(unknown file)", 0, "(unknown function)", None

    def getPackageLogger(self, name):
        """Get package logger"""
        if name not in self.__packages:
            self.__packages[name] = KbotPackageLogger(name, self)
        return self.__packages[name]

    def addPackage(self, name, level):
        """Log this package"""
        self.__filters[name] = level

    def remPackage(self, name):
        """Remove this package from logging"""
        if name == "all":
            return
        self.__filters.pop(name, None)

    def buildHandler(self, level, path=None):
        """Build handlers according the entry point.

        GetProducts generates a side effect, the logs are deactivated
        if the code is launched from there.

        If RunBot, we use two handlers
            one for kbot with 10 backup files
            one for datadog with 1 backup file

        In any other cases a simple streamer is done
        """
        if os.path.basename(sys.argv[0]).startswith("GetProduct"):
            self.addHandler(logging.NullHandler())
            return

        if os.path.basename(sys.argv[0]).startswith("RunBot"):
            datadog_handler = RotatingFileHandler(
                os.path.join(os.environ["KBOT_HOME"], "logs", "core.json"),
                maxBytes=5 * 1024 * 1024,
                backupCount=1,
            )
            datadog_handler.setFormatter(DataDogFormatter())
            datadog_handler.setLevel(level)
            self.addHandler(datadog_handler)

            kbot_handler = RotatingFileHandler(
                os.path.join(os.environ["KBOT_HOME"], "logs", "core.log"),
                maxBytes=5 * 1024 * 1024,
                backupCount=10,
            )
            kbot_handler.setFormatter(KbotFormatter())
            kbot_handler.setLevel(level)
            self.addHandler(kbot_handler)
            return

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(KbotFormatter())
        handler.setLevel(level)
        self.addHandler(handler)


class KbotLogEntry:
    def __init__(self, message):
        self.message = message
        self.ts = time.time()
        self.count = 1

    def Increase(self):
        self.count += 1


class KbotPackageLogger:
    def __init__(self, name, klogger):
        self.name = name
        self.logger = klogger

        # key: message hash
        # value: Instance of KbotLogEntry
        self.ONE_TIME_MESSAGES = {}

    def fine(self, msg, *args, **kwargs):
        return self._log("fine", msg, *args, **kwargs)

    def finest(self, msg, *args, **kwargs):
        return self._log("finest", msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        return self._log("debug", msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        return self._log("info", msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return self._log("warning", msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        return self._log("warn", msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return self._log("error", msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        return self._log("exception", msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return self._log("critical", msg, *args, **kwargs)

    def log(
        self,
        error: "ErrorCode",
        message=None,
        *args,
        exc_info=None,
        level=None,
        **kwargs,
    ):
        # Log messages are NOT DESIGNED TO BE EXCLUDED
        # Not checking for the isEnabledFor

        level = level or error.level
        message = message or error.message
        self._log(level, message, *args, **kwargs)

    def log_and_raise(
        self,
        error: "ErrorCode",
        message=None,
        *args,
        exc_info=None,
        level=None,
        **kwargs,
    ):
        self.log(error, message, exc_info=exc_info, level=level, **kwargs)
        raise error

    def _log(self, func, msg, *args, **kwargs):
        kwargs["package"] = self.name
        return getattr(self.logger, func)(msg, *args, **kwargs)

    def oneTime(self, level, msg, *args, **kwargs):
        expanded_message = msg % args
        message_hash = hash(expanded_message)

        message_log_entry = self.ONE_TIME_MESSAGES.get(message_hash)
        if message_log_entry:
            message_log_entry.Increase()
        else:
            self.ONE_TIME_MESSAGES[message_hash] = KbotLogEntry(expanded_message)

            # Get the related level function ("def warn" for example) and call it
            getattr(self, level)(msg, *args, **kwargs)


def _derive_kmodule(record: logging.LogRecord) -> str:
    """Turn '__init__' records into '<parent_package>.__init__' for readability."""
    if record.module == "__init__":
        return "%s.%s" % (
            os.path.split(os.path.dirname(record.pathname))[-1],
            record.module,
        )
    return record.module


class KbotFormatter(logging.Formatter):
    """Kbot formatter."""

    def __init__(self):
        super().__init__(
            "%(asctime)s - %(kmodule)s::%(funcName)s(%(lineno)s) - %(package)s - %(levelname)s - %(threadName)s - %(message)s"
        )

    @override
    def format(self, record):
        record.kmodule = _derive_kmodule(record)
        return super().format(record)


class DataDogFormatter(JsonFormatter):
    @override
    def format(self, record):
        record.kmodule = _derive_kmodule(record)
        return super().format(record)

    @override
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get("timestamp"):
            # this doesn't use record.created, so it is slightly off
            now = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            log_record["timestamp"] = now
        log_record["level"] = (log_record.get("level") or record.levelname).upper()


logging.addLevelName(FINE, "FINE")
logging.addLevelName(FINEST, "FINEST")
logging.setLoggerClass(KbotLogger)
log = cast(KbotLogger, logging.getLogger("kbot"))
# WARNING: This might not be a real fix but a work-around.
# I did not find the root cause of the log duplication.
log.propagate = False
log.buildHandler(levels[glevel])
log.setLevel(levels[glevel])
logger: KbotLogger = log
logging.setLoggerClass(logging.Logger)

mylogger = logger.getPackageLogger("utils")

#
# Here we have the custom code to be able to manage levels at runtime
#


def UpdateLevel(newLevel: int):
    """Update level for logging"""
    newValue = levels[NormalizeLevel(newLevel)]
    logger.setLevel(newValue)
    for h in log.handlers[:]:
        h.setLevel(newValue)


def _parse_debug_command(cmd: str):
    """Parse a runtime 'add <packages>[,...] <level>' or 'rem <packages>[,...]' command.

    Returns a (mode, package_names, level) tuple, or None when malformed.
    ``level`` is unused (0) for 'rem'.
    """
    mode, _, rest = cmd.partition(" ")
    mode = mode.strip()
    if mode not in ("add", "rem") or not rest:
        return None

    tokens = rest.split(" ")
    packages = [p.strip() for p in tokens[0].strip().split(",")]

    if mode == "rem":
        return mode, packages, 0

    if len(tokens) < 2:
        return None
    try:
        level = int(tokens[1])
    except ValueError:
        return None
    return mode, packages, level


def _apply_debug_command(mode: str, package: str, level: int) -> None:
    """Add or remove a single package's debug override, swallowing errors."""
    try:
        if mode == "add":
            mylogger.debug("Addpackage(%s, %s)", package, levels[NormalizeLevel(level)])
            logger.addPackage(package, levels[NormalizeLevel(level)])
        else:
            mylogger.debug("Rempackage(%s, %s)", package)
            logger.remPackage(package)
    except Exception as e:
        print("EXC :", str(e))
        sys.stdout.flush()


def UpdateSupportedPackages(cmd):
    mylogger.debug("UpdateSupportedPackages: '%s'", cmd)

    parsed = _parse_debug_command(cmd)
    if parsed is None:
        mylogger.warning("Invalid logger command")
        return

    mode, packages, level = parsed
    for package in packages:
        _apply_debug_command(mode, package, level)
