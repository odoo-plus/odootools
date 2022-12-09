import os
from pathlib import Path
import logging
import platform

from .base import Plugin

_logger = logging.getLogger(__name__)


class LoggerPlugin(Plugin):
    def __init__(self):
        super().__init__()

        self._format = None
        self._handler = None
        self._formatter = None
        self._perf_filter = None

    def get_formatter(self, record_format):
        from odoo.netsvc import DBFormatter
        return DBFormatter(record_format)

    def get_format(self):
        return (
            '%(asctime)s %(pid)s %(levelname)s %(dbname)s %(name)s: '
            '%(message)s %(perf_info)s'
        )

    def get_perf_filter(self):
        from odoo.netsvc import PerfFilter
        return PerfFilter()

    @property
    def handler(self):
        if not self._handler:
            self._handler = self.get_handler()
        return self._handler

    @property
    def format(self):
        if not self._format:
            self._format = self.get_format()
        return self._format

    @property
    def formatter(self):
        if not self._formatter:
            self._formatter = self.get_formatter(self.format)
        return self._formatter

    @property
    def perf_filter(self):
        if not self._perf_filter:
            self._perf_filter = self.get_perf_filter()
        return self._perf_filter


class SysLogPlugin(LoggerPlugin):
    def __init__(self, description, version):
        super().__init__()
        self.description = description
        self.version = version

    def get_handler(self):
        # SysLog Handler
        if os.name == 'nt':
            handler = logging.handlers.NTEventLogHandler(
                f"{self.description} {self.version}"
            )
        elif platform.system() == 'Darwin':
            handler = logging.handlers.SysLogHandler('/var/run/log')
        else:
            handler = logging.handlers.SysLogHandler('/dev/log')

        return handler

    def get_format(self):
        return (
            f"{self.description} {self.version}:"
            f"%(dbname)s:%(levelname)s:%(name)s:%(message)s"
        )


class FileLogPlugin(LoggerPlugin):
    def __init__(self, path):
        super().__init__()
        self.path = Path(path)

    def get_handler(self):
        # LogFile Handler
        logf = str(self.path)

        # We check we have the right location for the log files
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if os.name == 'posix':
            handler = logging.handlers.WatchedFileHandler(logf)
        else:
            handler = logging.FileHandler(logf)

        return handler


class StreamLogPlugin(LoggerPlugin):
    def __init__(self, no_tty=None):
        super().__init__()
        self.no_tty = no_tty

    def get_handler(self):
        return logging.StreamHandler()

    def get_formatter(self, record_format):
        if self.is_tty():
            from odoo.netsvc import ColoredFormatter
            return ColoredFormatter(record_format)
        else:
            return super().get_formatter(record_format)

    def get_perf_filter(self):
        if self.is_tty():
            from odoo.netsvc import ColoredPerfFilter
            return ColoredPerfFilter()
        else:
            return super().get_perf_filter()

    def is_tty(self):
        if self.no_tty is not None and self.no_tty:
            return False

        stream = self.handler.stream
        return hasattr(stream, 'fileno') and os.isatty(stream.fileno())


class JsonFormatter(logging.Formatter):
    def format(self, record):
        import json

        data = {
            "message": record.getMessage(),
            "msg": record.msg,
            "args": [str(arg) for arg in record.args],
            "level": record.levelname,
            "filename": record.pathname,
            "logger": record.name,
            "pid": record.process,
        }

        return json.dumps(data)


class JsonStreamLogPlugin(StreamLogPlugin):
    def get_formatter(self, record_format):
        return JsonFormatter()


DEFAULT_LOG_CONFIGURATION = [
    'odoo.http.rpc.request:INFO',
    'odoo.http.rpc.response:INFO',
    ':INFO',
]

PSEUDOCONFIG_MAPPER = {
    'debug_rpc_answer': [
        'odoo:DEBUG', 'odoo.sql_db:INFO', 'odoo.http.rpc:DEBUG'
    ],
    'debug_rpc': [
        'odoo:DEBUG', 'odoo.sql_db:INFO', 'odoo.http.rpc.request:DEBUG'
    ],
    'debug': ['odoo:DEBUG', 'odoo.sql_db:INFO'],
    'debug_sql': ['odoo.sql_db:DEBUG'],
    'info': [],
    'runbot': ['odoo:RUNBOT', 'werkzeug:WARNING'],
    'warn': ['odoo:WARNING', 'werkzeug:WARNING'],
    'error': ['odoo:ERROR', 'werkzeug:ERROR'],
    'critical': ['odoo:CRITICAL', 'werkzeug:CRITICAL'],
}


class LoggingPlugin(Plugin):
    def __init__(self, logger_type=None, log_handler=None, log_level='info'):
        if logger_type is None:
            logger_type = StreamLogPlugin()

        if log_handler is None:
            log_handler = [':INFO']

        self.logger_type = logger_type
        self.log_handler = log_handler
        self.log_level = log_level

    def register(self, app):
        super().register(app)
        self.logger_type.register(app)

    def prepare_environment(self):
        handler = self.logger_type.handler
        formatter = self.logger_type.formatter
        perf_filter = self.logger_type.perf_filter

        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.getLogger('werkzeug').addFilter(perf_filter)

        self.init_record_factory()
        self.setup_log_levels()

    def init_record_factory(self):
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.perf_info = ""
            return record

        logging.setLogRecordFactory(record_factory)

    def setup_log_levels(self):
        # Configure loggers levels
        pseudo_config = PSEUDOCONFIG_MAPPER.get(self.log_level, [])
        # pseudo_config = PSEUDOCONFIG_MAPPER.get("debug_sql", [])

        logconfig = self.log_handler

        logging_configurations = (
            DEFAULT_LOG_CONFIGURATION + pseudo_config + logconfig
        )
        for logconfig_item in logging_configurations:
            loggername, level = logconfig_item.strip().split(':')
            level = getattr(logging, level, logging.INFO)
            logger = logging.getLogger(loggername)
            logger.setLevel(level)

        for logconfig_item in logging_configurations:
            _logger.debug('logger level set: "%s"', logconfig_item)
