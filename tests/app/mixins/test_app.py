import pytest
from mock import MagicMock, patch

from odoo_tools.app.mixins.app import (
    AppMixin,
    SessionStoreMixin,
    EnvironmentManagerMixin,
    DbRequestMixin
)

from odoo_tools.app.mixins.request import (
    SessionManagementMixin,
    DbManagementMixin
)


def test_app_mixin():
    class Mixin(AppMixin):
        pass

    obj = Mixin()

    assert isinstance(obj, AppMixin)


def test_session_store_mixin():
    session_store = SessionStoreMixin()

    assert session_store._session_store is None
    assert session_store.execute_session_gc is False

    session_store.session_gc()

    with pytest.raises(NotImplementedError):
        session_store.make_session_store()


def test_custom_session_store():
    class Base(object):
        def _request_type(self):
            return [object]

    class CustomSessionStore(SessionStoreMixin):
        def make_session_store(self):
            store = MagicMock()
            store.is_store = True
            return store

    CustomType = type('CustomType', (CustomSessionStore, Base), {})

    session_store = CustomType()

    store = session_store.session_store

    assert store.is_store is True

    assert session_store._request_type() == [object]


def test_environment_mixin():
    class Dispatcher(object):
        def dispatch(self, environ, start_response):
            return start_response(environ)

    CustomType = type('Custom', (EnvironmentManagerMixin, Dispatcher), {})

    obj = CustomType()

    environ = MagicMock()

    api = MagicMock()

    modules = {
        "odoo": MagicMock(),
        "odoo.api": api
    }

    with patch.dict('sys.modules', modules):
        result = obj.dispatch(environ, lambda param: param)
        assert result == environ
        api.Environment.manage.assert_called_once()


def test_db_mixin():
    class Db(object):
        def _request_type(self):
            return [object]

    Custom = type('Custom', (DbRequestMixin, Db), {})

    obj = Custom()

    req_type = obj._request_type()

    assert req_type == [DbManagementMixin, object]
