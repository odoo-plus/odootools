import pytest
from mock import MagicMock, patch
from odoo_tools.app.mixins.request import (
    BaseRequestMixin,
    BaseRequest,
    BaseHTTPRequest,
    SessionManagementMixin,
    WebManagementMixin,
    DbManagementMixin,
    RequestDispatcher,
    Request
)


@pytest.fixture
def modules():
    return {
        "odoo": MagicMock(),
        "odoo.api": MagicMock(),
        "odoo.service": MagicMock(),
        "odoo.http": MagicMock(),
        "odoo.tools": MagicMock(),
        "odoo.tools.debugger": MagicMock(),
        "werkzeug": MagicMock(),
        "werkzeug.exceptions": MagicMock(),
        "werkzeug.urls": MagicMock(),
        "werkzeug.wrappers": MagicMock(),
        "werkzeug.utils": MagicMock(),
    }


class MockRedirect(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class MockUrl(object):
    def __init__(self, url):
        self.url = url

    def replace(self, **kwargs):
        return self

    def to_url(self):
        return self.url


class MockException(Exception):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class MockNotFound(MockException):
    pass


class MockPostmortenException(MockException):
    pass


class MockHTTPException(MockException):
    pass


def test_base_mixin():
    app = MagicMock()
    httprequest = MagicMock()

    request = BaseRequestMixin(app, httprequest)
    assert request.app == app
    assert hasattr(request, 'httprequest') is False


def test_http_request():
    app = MagicMock()
    httprequest = MagicMock()

    request = BaseHTTPRequest(app, httprequest)
    assert request.app == app
    assert request.httprequest == httprequest


def test_base_request(modules):
    app = MagicMock()
    httprequest = MagicMock()
    request = BaseRequest(app, httprequest)

    request.pre_dispatch()
    request.post_dispatch(MagicMock())

    resp1 = MagicMock()
    resp = request.get_response(resp1)
    assert resp == resp1

    modules['odoo.http'].NO_POSTMORTEM = MockPostmortenException
    modules['werkzeug.exceptions'].HTTPException = MockHTTPException

    post_mortem = modules['odoo.tools.debugger'].post_mortem

    with patch.dict('sys.modules', modules):
        with pytest.raises(Exception):
            request._handle_exception(Exception("hey"))

        post_mortem.assert_called_once()

        post_mortem.reset_mock()

        with pytest.raises(MockPostmortenException):
            request._handle_exception(MockPostmortenException())

        post_mortem.assert_not_called()

        with pytest.raises(MockHTTPException):
            request._handle_exception(MockHTTPException())

        post_mortem.assert_not_called()


def test_session_mixin(modules):
    """
    Simple test for the session mixin but need rework.
    """
    app = MagicMock()

    Custom = type('Custom', (SessionManagementMixin, BaseRequest), {})

    with patch.dict('sys.modules', modules):
        httprequest = MagicMock()
        httprequest.args = {}
        httprequest.headers = {}
        httprequest.cookies = {
            "session_id": "sissid"
        }

        app.session_store = MagicMock()

        request = Custom(app, httprequest)
        # TODO cleanup inheritance of mixins
        request.env = MagicMock()
        request.pre_dispatch()
        response = request.get_response("")
        request.post_dispatch(response)
        # Get Response shouldn't alter the type of the response
        # in practice it's getting a Response
        assert response == ""


def test_web_management_mixin(modules):
    app = MagicMock()
    httprequest = MagicMock()

    urls = modules['werkzeug.urls']
    urls.URL = MockUrl
    urls.url_parse = MockUrl
    urls.url_encode = lambda query: '&'.join([
        f"{key}={value}" for key, value in query.items()
    ])

    wk = modules['werkzeug.exceptions']
    wk.NotFound = MockNotFound

    wku = modules['werkzeug.utils']
    wku.redirect = MockRedirect

    with patch.dict('sys.modules', modules):
        request = WebManagementMixin(app, httprequest)
        result = request.handle_redirect_location("/web")
        assert result == "/web"

        result = request.handle_redirect_location(MockUrl("/web"))
        assert result == "/web"

        resp = request.not_found("not here")
        assert isinstance(resp, MockNotFound)

        new_loc = request.redirect_query("/web", {"db": "test"})
        assert isinstance(new_loc, MockRedirect)
        assert new_loc.args[0] == "/web?db=test"


def test_request_dispatcher():
    app = MagicMock()
    httprequest = MagicMock()

    request = RequestDispatcher(app, httprequest)

    params = request.get_http_params()
    assert params == {}

    httprequest.args = {"a": 1}
    httprequest.form = {"b": 2}
    httprequest.files = {"c": 3}

    params = request.get_http_params()

    assert params == {"a": 1, "b": 2, "c": 3}

    httprequest.form = {"b": 3, "a": 2, "c": 2}

    # Form can override args but cannot override files
    params = request.get_http_params()
    assert params == {"a": 2, "b": 3, "c": 3}

    # Session id is dropped but not other keys
    httprequest.args = {"a": 1, "session_id": "hey", "v": 1}
    params = request.get_http_params()
    assert params == {"a": 2, "b": 3, "c": 3, "v": 1}

    request.dispatcher = MagicMock()
    request.dispatch()

    request.dispatcher.dispatch.assert_called_once()

    request.args = 1
    assert request.endpoint_arguments == 1


def test_db_management(modules):
    app = MagicMock()
    httprequest = MagicMock()
    httprequest.session.uid = 1
    httprequest.session.db = 'test'

    with patch('sys.modules', modules):
        request = DbManagementMixin(app, httprequest)

        assert request.lang is None
        assert request.uid != 1

        request.session.db = 'test'
        assert request.session.db == 'test'

        env = request.env
        assert env == request.env
        request.uid = 2
        assert env != request.env

        request.session.db = None
        assert request.db is None

        request.context = {'a': 1}
        assert request.context != {'a': 1}

        request.pre_dispatch()
        request.dispatch()
        request.post_dispatch('')


def test_request_full(modules):
    app = MagicMock()
    httprequest = MagicMock()

    Custom = type(
        'Custom',
        (
            DbManagementMixin,
            # SessionManagementMixin,
            Request,
        ),
        {}
    )

    with patch('sys.modules', modules):
        request = Custom(app, httprequest)
