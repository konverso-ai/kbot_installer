""" KBot logger."""
import sys
import os
import datetime
import time
import warnings
import io
import traceback
import logging
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

from pythonjsonlogger.json import JsonFormatter

if TYPE_CHECKING:
    from kerrors.base import ErrorCode

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
    5: FINEST
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

_srcfile = os.path.normcase(NormalizeLevel.__code__.co_filename)


class KbotLogRecord(logging.LogRecord):
    def __init__(
        self,
        name,
        level,
        pathname,
        lineno,
        msg,
        args,
        exc_info,
        func=None,
        sinfo=None,
        package='',
        **kwargs,
    ) -> None:
        super().__init__(
            name,
            level,
            pathname,
            lineno,
            msg,
            args,
            exc_info,
            func,
            sinfo,
            **kwargs,
        )
        self.package = package


class KbotLogger(logging.Logger):
    """Logger for Kbot"""
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

        # key: a package name
        # value: a KbotPackage object
        self.__packages = {}

        # Will filter based on the debug add/rm options
        self.__filters = {}

    @property
    def packages(self):
        """Returns an iterator that contains all the registered package names"""
        return self.__packages.keys()

    def setLevel(self, level):
        self.addPackage("all", level)

    def fine(self, msg, *args, **kwargs):
        """FINE debug level"""
        if self.isEnabledFor(FINE, **kwargs):
            self._log(FINE, msg, args, **kwargs)

    def finest(self, msg, *args, **kwargs):
        """FINEST debug level"""
        if self.isEnabledFor(FINEST, **kwargs):
            self._log(FINEST, msg, args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.DEBUG, **kwargs):
            self._log(logging.DEBUG, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.INFO, **kwargs):
            self._log(logging.INFO, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.WARNING, **kwargs):
            self._log(logging.WARNING, msg, args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        warnings.warn("The 'warn' method is deprecated, "
                      "use 'warning' instead", DeprecationWarning, 2)
        self.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.ERROR, **kwargs):
            self._log(logging.ERROR, msg, args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.CRITICAL, **kwargs):
            self._log(logging.CRITICAL, msg, args, **kwargs)

    def isEnabledFor(self, level, **kwargs):
        package = kwargs.get('package', 'all')
        if package not in self.__filters:
            package = 'all'
        return level >= self.__filters[package].level

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, package=''):
        #if self.isPackageSupported(package):
        #    super()._log(level, msg, args, exc_info, extra, stack_info)

        sinfo = None
        if _srcfile:
            #IronPython doesn't track Python frames, so findCaller raises an
            #exception on some versions of IronPython. We trap it here so that
            #IronPython can use logging.
            try:
                fn, lno, func, sinfo = self.findCaller(stack_info, package)
            except ValueError: # pragma: no cover
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        else: # pragma: no cover
            fn, lno, func = "(unknown srcfile)", 0, "(unknown srcfunction)"
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        record = self.makeRecord(self.name, level, fn, lno, msg, args,
                                 exc_info, func, extra, sinfo, package)
        self.handle(record)

    def findCaller(self, stack_info=False, package=''):
        if package:
            f = sys._getframe(4)
        else:
            f = sys._getframe(2)
        #On some versions of IronPython, currentframe() returns None if
        #IronPython isn't run with -X:Frames.
        if f is not None:
            f = f.f_back
        rv = "(unknown file)", 0, "(unknown function)", None
        while hasattr(f, "f_code"):
            co = f.f_code

            filename = os.path.normcase(co.co_filename)
            if filename == _srcfile:
                f = f.f_back
                continue
            sinfo = None
            if stack_info:
                sio = io.StringIO()
                sio.write('Stack (most recent call last):\n')
                traceback.print_stack(f, file=sio)
                sinfo = sio.getvalue()
                if sinfo[-1] == '\n':
                    sinfo = sinfo[:-1]
                sio.close()
            rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
            break
        return rv

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None, package=''):
        rv = KbotLogRecord(name, level, fn, lno, msg, args, exc_info, func,
                           sinfo, package)
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in rv.__dict__):
                    raise KeyError("Attempt to overwrite %r in LogRecord" % key)
                rv.__dict__[key] = extra[key]
        return rv

    def getPackageLogger(self, name):
        """Get package logger"""
        if name not in self.__packages:
            self.__packages[name] = KbotPackageLogger(name, self)
        return self.__packages[name]

    def addPackage(self, name, level):
        """Log this package"""
        if name not in self.__filters:
            self.__filters[name] = KbotPackageFilter(name, level)
        else:
            self.__filters[name].level = level

    def remPackage(self, name):
        """Remove this package from logging"""
        if name == 'all':
            return
        if name in self.__filters:
            del self.__filters[name]

    def buildHandler(self, level, path=None):
        """Build handlers according the entry point.

        GetProducts generates a side effect, the logs are deactivated
        if the code is launched from there.

        If RunBot, we use two handlers
            one for kbot with 10 backup files
            one for datadog with 1 backup file

        In any other cases a simple streamer is done
        """
        if os.path.basename(sys.argv[0]).startswith('GetProduct'):
            self.addHandler(logging.NullHandler())
        elif os.path.basename(sys.argv[0]).startswith('RunBot'):
            self.addHandler(DataDogHandler(level, path))
            self.addHandler(KbotHandler(level, path))
        else:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(KbotFormatter())
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

        #for func in ('fine', 'finest', 'debug', 'info', 'warning', 'warn', 'error', 'exception', 'critical'):
        #    setattr(self, func, getattr(self.logger, func))

    def fine(self, msg, *args, **kwargs):
        return self._log('fine', msg, *args, **kwargs)

    def finest(self, msg, *args, **kwargs):
        return self._log('finest', msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        return self._log('debug', msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        return self._log('info', msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return self._log('warning', msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        return self._log('warn', msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return self._log('error', msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        return self._log('exception', msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return self._log('critical', msg, *args, **kwargs)

    def log(self, error: "ErrorCode", message, *args, exc_info=None, level=None, **kwargs):
        # Log messages are NOT DESIGNED TO BE EXCLUDED
        # Not checking for the isEnabledFor

        level = level or error.level
        message = message or error.message
        self._log(level, message, *args, **kwargs)

    def log_and_raise(self, error: "ErrorCode", message, *args, exc_info=None, level=None, **kwargs):
        self.log(error=error, message=message, *args, exc_info=exc_info, level=level, **kwargs)
        raise error

    def _log(self, func, msg, *args, **kwargs):
        kwargs['package'] = self.name
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


class KbotFormatter(logging.Formatter):
    """Kbot formatter."""
    def __init__(self):
        super().__init__('%(asctime)s - %(kmodule)s::%(funcName)s(%(lineno)s) - %(package)s - %(levelname)s - %(threadName)s - %(message)s')

    def format(self, record):
        if record.module == '__init__':
            record.kmodule = '%s.%s'%(os.path.split(os.path.dirname(record.pathname))[-1], record.module)
        else:
            record.kmodule = record.module
        return super().format(record)


class DataDogFormatter(JsonFormatter):
    def format(self, record):
        if record.module == '__init__':
            record.kmodule = '%s.%s'%(os.path.split(os.path.dirname(record.pathname))[-1], record.module)
        else:
            record.kmodule = record.module
        return super().format(record)

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


class KbotHandler:
    def __init__(self, level, path=None):
        self.level = logging.NOTSET
        self.handler = RotatingFileHandler(
            os.path.join(os.environ['KBOT_HOME'], 'logs', 'core.log'),
            maxBytes=5 * 1024 * 1024,
            backupCount=10,
        )
        self.handler.setFormatter(KbotFormatter())
        self.__filters = {}

    def filter(self, record):
        return True

    def handle(self, record):
        if self.filter(record):
            return self.handler.handle(record)
        return False

    def setLevel(self, level):
        self.handler.setLevel(level)


class DataDogHandler:
    def __init__(self, level, path=None):
        self.level = logging.NOTSET
        self.handler = RotatingFileHandler(
            os.path.join(os.environ['KBOT_HOME'], 'logs', 'core.json'),
            maxBytes=5 * 1024 * 1024,
            backupCount=1,
        )
        self.handler.setFormatter(DataDogFormatter())
        self.__filters = {}

    def filter(self, record):
        return True

    def handle(self, record):
        if self.filter(record):
            return self.handler.handle(record)
        return False

    def setLevel(self, level):
        self.handler.setLevel(level)


class KbotPackageFilter:
    def __init__(self, name, level):
        self.name = name
        self.level = level

    def filter(self, record):
        sys.stdout.flush()
        if self.name in ('all', record.package) and record.levelno >= self.level:
            return True
        return False


logging.addLevelName(FINE, 'FINE')
logging.addLevelName(FINEST, 'FINEST')
logging.setLoggerClass(KbotLogger)
log = logging.getLogger('kbot')
# WARNING: This might not be a real fix but a work-around.
# I did not find the root cause of the log duplication.
log.propagate = False
log.buildHandler(levels[glevel])
#if os.path.basename(sys.argv[0]).startswith('RunBot'):
#    handler = RotatingFileHandler(os.path.join(os.environ['KBOT_HOME'], 'logs', 'core.log'), maxBytes=5000000, backupCount=10)
#else:
#    handler = logging.StreamHandler(sys.stdout)
#handler.setFormatter(KbotFormatter())
#handler.setLevel(levels[glevel])
#log.addHandler(handler)
log.setLevel(levels[glevel])
logger = log
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


def UpdateSupportedPackages(cmd):
    mylogger.debug("UpdateSupportedPackages: '%s'", cmd)
    data = cmd.split(' ', 1)
    mode = data[0].strip()
    if mode in ('add', 'rem') and len(data) > 1:
        data = data[1].split(' ')
        packages = data[0].strip()
        if mode == 'add' and len(data) < 2:
            return
        level = 0
        if mode == 'add':
            try:
                level = int(data[1])
            except:
                return
        packages = [p.strip() for p in packages.strip().split(',')]
        for package in packages:
            try:
                if mode == 'add':
                    mylogger.debug("Addpackage(%s, %s)", package, levels[NormalizeLevel(level)])
                    logger.addPackage(package, levels[NormalizeLevel(level)])
                elif mode == 'rem':
                    mylogger.debug("Rempackage(%s, %s)", package)
                    logger.remPackage(package)
            except Exception as e:
                print("EXC :", str(e))
                sys.stdout.flush()
    else:
        mylogger.warning("Invalid logger command")
