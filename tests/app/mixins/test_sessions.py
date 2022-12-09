import pytest
from mock import patch, MagicMock

from odoo_tools.app.mixins.sessions import FileSystemSessionStoreMixin


@pytest.fixture
def modules():
    return {
        'odoo': MagicMock(),
        'odoo.http': MagicMock()
    }


class MockSessionStore(object):
    def __init__(self, session_dir, session_class, renew_missing=False):
        self.path = session_dir
        self.session_class = session_class
        self.renew_missing = renew_missing


class MockSession(object):
    pass


def test_fs_mixin(modules):
    app = MagicMock()

    class BaseApp(object):
        def __init__(self, application):
            self.app = application

    Custom = type('Custom', (FileSystemSessionStoreMixin, BaseApp), {})

    store = Custom(app)

    http = modules['odoo.http']
    http.sessions.FilesystemSessionStore = MockSessionStore
    http.Session = MockSession

    with patch.dict('sys.modules', modules), \
         patch('os.listdir') as lsdir, \
         patch('os.path.getmtime') as getm, \
         patch('os.unlink') as unlink, \
         patch('random.random') as rand, \
         patch('time.time') as time:

        sstore = store.make_session_store()
        assert isinstance(sstore, MockSessionStore)

        sstore = store.session_store
        assert isinstance(sstore, MockSessionStore)

        sstore2 = store.session_store
        assert sstore == sstore2

        rand.return_value = 1
        store.session_gc()
        time.assert_not_called()

        getm.return_value = 50
        lsdir.return_value = ['x.sess']
        rand.return_value = 0
        time.return_value = 0
        store.session_gc(delta=10)
        time.assert_called_once()
        unlink.assert_not_called()

        time.reset_mock()
        getm.return_value = -50

        store.session_gc(delta=10)
        time.assert_called_once()
        unlink.assert_called_once()

        time.reset_mock()
        unlink.reset_mock()
        unlink.side_effect = OSError("Can't unlink")

        store.session_gc(delta=10)
        time.assert_called_once()
        unlink.assert_called_once()
