import json
from pathlib import Path
import pytest
from mock import patch, MagicMock
from odoo_tools.app.plugins.logging import (
    LoggerPlugin,
    SysLogPlugin,
    FileLogPlugin,
    StreamLogPlugin,
    JsonFormatter,
    JsonStreamLogPlugin,
    LoggingPlugin,
)


@pytest.fixture
def modules():
    odoo = MagicMock()

    return {
        "odoo": odoo,
        "odoo.netsvc": odoo.netsvc
    }


class MockFormatter(object):
    def __init__(self, forma):
        self.forma = forma


class MockFilter(object):
    pass


def test_logger_plugin(modules):
    plugin = LoggerPlugin()

    assert plugin.format is not None

    with pytest.raises(AttributeError):
        plugin.handler

    odoo = modules['odoo']

    odoo.netsvc.DBFormatter = MockFormatter
    odoo.netsvc.PerfFilter = MockFilter

    with patch.dict('sys.modules', modules):
        formatter = plugin.formatter
        assert isinstance(formatter, MockFormatter)

        filter = plugin.perf_filter
        assert isinstance(filter, MockFilter)
        # with pytest.raises(AttributeError):


def test_syslog_plugin(modules):
    plugin = SysLogPlugin("odoo", "15.0")

    assert plugin.description == "odoo"
    assert plugin.version == "15.0"

    with patch('os.name', 'nt'), \
         patch('logging.handlers.NTEventLogHandler') as nt:
        plugin = SysLogPlugin("odoo", "15.0")
        handler = plugin.handler
        assert handler._mock_new_parent == nt

    with patch('os.name', 'posix'), \
         patch('logging.handlers.SysLogHandler') as syslog, \
         patch('platform.system') as system:
        system.return_value = 'Darwin'
        plugin = SysLogPlugin("odoo", "15.0")
        handler = plugin.handler
        syslog.assert_called_with('/var/run/log')

    with patch('os.name', 'posix'), \
         patch('logging.handlers.SysLogHandler') as syslog, \
         patch('platform.system') as system:
        system.return_value = 'Linux'
        plugin = SysLogPlugin("odoo", "15.0")
        handler = plugin.handler
        syslog.assert_called_with('/dev/log')

    plugin2 = LoggerPlugin()

    assert plugin.format is not None
    assert plugin.format != plugin2.format


def test_filelog_plugin(modules):
    plugin = FileLogPlugin('/test/mod.log')
    assert plugin.path == Path('/test/mod.log')

    with patch('os.name', 'posix'), \
         patch('logging.handlers.WatchedFileHandler') as wf, \
         patch.object(Path, 'mkdir') as mkdir:
        handler = plugin.handler
        assert handler._mock_new_parent == wf
        wf.assert_called_with('/test/mod.log')
        mkdir.assert_called_once()

    # Create here to prevent creating nt Path
    plugin = FileLogPlugin('/test/mod.log')
    with patch('os.name', 'nt'), \
         patch('logging.FileHandler') as wf, \
         patch.object(Path, 'mkdir') as mkdir:
        handler = plugin.handler
        assert handler._mock_new_parent == wf
        wf.assert_called_with('/test/mod.log')
        mkdir.assert_called_once()


def test_streamlog_plugin(modules):
    plugin = StreamLogPlugin(no_tty=True)
    assert plugin.is_tty() is False

    with patch.dict('sys.modules', modules), \
         patch('logging.StreamHandler') as st, \
         patch('os.isatty') as is_tty, \
         patch('odoo.netsvc.ColoredFormatter') as cf, \
         patch('odoo.netsvc.ColoredPerfFilter') as cpf:
        is_tty.return_value = True
        handler = MagicMock()
        st.return_value = handler
        handler.stream.fileno.return_value = 1
        assert plugin.is_tty() is False

        plugin.no_tty = False
        assert plugin.is_tty() is True

        is_tty.return_value = False
        assert plugin.is_tty() is False

        is_tty.return_value = True
        del handler.stream.fileno
        assert plugin.is_tty() is False

        formatter = plugin.formatter
        assert formatter._mock_new_parent != cf

        perf_filter = plugin.perf_filter
        assert perf_filter._mock_new_parent != cpf

    plugin = StreamLogPlugin(no_tty=False)
    with patch.dict('sys.modules', modules), \
         patch('logging.StreamHandler') as st, \
         patch('os.isatty') as is_tty, \
         patch('odoo.netsvc.ColoredFormatter') as cf, \
         patch('odoo.netsvc.ColoredPerfFilter') as cpf:
        is_tty.return_value = True
        handler = MagicMock()
        handler.stream.fileno.return_value = 1
        st.return_value = handler

        assert plugin.handler == handler
        assert plugin.is_tty() is True

        formatter = plugin.formatter
        assert formatter._mock_new_parent == cf

        perf_filter = plugin.perf_filter
        assert perf_filter._mock_new_parent == cpf


def test_json_formatter():
    formatter = JsonFormatter()

    record = MagicMock()

    record.getMessage.return_value = "hello"
    record.msg = "hellos"
    record.args = [1, 2, 3]
    record.levelname = "INFO"
    record.pathname = "test.py"
    record.name = "test"
    record.process = 1

    result = formatter.format(record)

    assert result == json.dumps({
        "message": "hello",
        "msg": "hellos",
        "args": ["1", "2", "3"],
        "level": "INFO",
        "filename": "test.py",
        "logger": "test",
        "pid": 1
    })

    plugin = JsonStreamLogPlugin()
    formatter = plugin.formatter

    assert isinstance(formatter, JsonFormatter)


def test_logging_plugin(modules):
    app = MagicMock()
    plugin = LoggingPlugin()

    assert isinstance(plugin.logger_type, StreamLogPlugin)
    assert plugin.log_handler == [':INFO']

    plugin.register(app)

    def make_rec_factory():
        store = {}

        def setLogRecordFactory(callback):
            mrecord = MagicMock()
            record = callback(mrecord)
            assert record.perf_info == ""
            store['exec'] = True

        return store, setLogRecordFactory

    store, setLogRecordFactory = make_rec_factory()

    def getLogRecordFactory():
        def factory(rec):
            return rec
        return factory

    with patch.dict('sys.modules', modules), \
         patch('logging.getLogRecordFactory', getLogRecordFactory), \
         patch('logging.setLogRecordFactory', setLogRecordFactory):
        plugin.prepare_environment()

    assert store == {'exec': True}
