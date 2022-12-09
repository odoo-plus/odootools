import pytest
from mock import patch, MagicMock
from pathlib import Path
from odoo_tools.app.mixins.request import Request
from odoo_tools.app.mixins.dispatchers import DispatcherNotFoundError, JsonDispatcher, JsonRpcDispatcher, HttpDispatcher
from odoo_tools.app.mixins.http import (
    AssetsMiddleware,
    StaticAssetsMiddleware,
    AddonsLoaderMiddleware,
    BaseApp,
    BaseWSGIApp
)


@pytest.fixture
def modules():
    return {
        "odoo": MagicMock(),
        "odoo.http": MagicMock(),
        "odoo.addons": MagicMock(),
        "odoo.modules": MagicMock(),
        "odoo.modules.module": MagicMock(),
        "odoo.modules.registry": MagicMock(),
        "odoo.tools._vendor.useragents": MagicMock(),
        "werkzeug": MagicMock(),
        "werkzeug.wrappers": MagicMock(),
        "werkzeug.exceptions": MagicMock(),
        "werkzeug.datastructures": MagicMock(),
    }


class BaseMock(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class MockNotFound(BaseMock, Exception):
    pass


class MockHTTPException(BaseMock, Exception):
    pass


class MockSpec(object):
    def __init__(self, module, paths):
        self.module = module
        self.submodule_search_locations = [paths]


class MockFileHandle(object):
    def __init__(self, mode):
        self.mode = mode


class MockResponse(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, environ, start_response):
        return self


def test_base_app():
    app = MagicMock()
    BaseApp(app)


def test_addons_loader(modules):
    app = MagicMock()

    odoo = modules['odoo']
    odoo.addons.__path__ = ['/test']

    http = modules['odoo.http']
    http.addons_manifest = {}

    def manifest(module):
        if module == 'blah':
            return None

        return {
            "name": module,
            "installable": True
        }

    module = modules['odoo.modules.module']
    module.load_information_from_description_file = manifest

    with patch.dict('sys.modules', modules), \
         patch('os.listdir') as ls:
        ls.return_value = ['base', 'web', 'blah', 'blah', 'web']
        Custom = type('Custom', (AddonsLoaderMiddleware, BaseApp), {})

        Custom(app)

        assert modules['odoo.http'].addons_manifest['base'] is not None


def test_assets_middleware():
    mid = AssetsMiddleware()

    path = mid.get_assets_path('/bargs/static/src/css/styles.css')
    assert path is None

    path = mid.get_assets_path('/bargs/src/css/styles.css')
    assert path is None

    with patch('odoo_tools.app.mixins.http.find_spec') as find_spec:
        find_spec.return_value = None
        path = mid.get_assets_path('/bargs/static/src/css/styles.css')
        assert path is None

    with patch('odoo_tools.app.mixins.http.find_spec') as find_spec, \
         patch.object(Path, 'exists') as exists:
        exists.return_value = True
        find_spec.return_value = MockSpec('base', '/test/base')
        path = mid.get_assets_path('/base/static/src/css/styles.css')
        assert path == Path("/test/base/static/src/css/styles.css")

    with patch('odoo_tools.app.mixins.http.find_spec') as find_spec, \
         patch.object(Path, 'exists') as exists:
        exists.return_value = False
        find_spec.return_value = MockSpec('base', '/test/base')
        path = mid.get_assets_path('/base/static/src/css/styles.css')
        assert path is None


def test_static_middleware(modules):
    class Base(object):
        def __init__(self, app):
            self.app = app

        def dispatch(self, environ, start_response):
            return start_response("nothing")

    Custom = type('Custom', (StaticAssetsMiddleware, Base), {})
    app = MagicMock()

    http = modules['werkzeug.wrappers']
    http.Response = MockResponse

    def start_response(env):
        return env

    with patch('odoo_tools.app.mixins.http.find_spec') as find_spec, \
         patch.dict('sys.modules', modules), \
         patch.object(Path, 'exists') as exists, \
         patch.object(Path, 'open') as openf:

        openf.side_effect = MockFileHandle

        mid = Custom(app)

        exists.return_value = False

        find_spec.return_value = MockSpec('base', '/test/base')

        # Not a static path return default dispatch
        environ = {
            "PATH_INFO": "/base/src/css/styles.css"
        }

        result = mid.dispatch(environ, start_response)
        assert result == "nothing"

        # No spec return default dispatch
        find_spec.return_value = None
        environ = {
            "PATH_INFO": "/base/static/src/css/styles.css"
        }

        result = mid.dispatch(environ, start_response)
        assert result == "nothing"

        # Check if module not found works and return the default dispatch
        find_spec.side_effect = ModuleNotFoundError("Base module not found")
        environ = {
            "PATH_INFO": "/base/static/src/css/styles.css"
        }

        result = mid.dispatch(environ, start_response)
        assert result == "nothing"

        # Should return default dispatch as file doesn't exists
        find_spec.return_value = MockSpec('base', '/test/base')
        find_spec.side_effect = None
        environ = {
            "PATH_INFO": "/base/static/src/css/styles.css"
        }

        result = mid.dispatch(environ, start_response)
        assert result == "nothing"

        find_spec.return_value = MockSpec('base', '/test/base')
        exists.return_value = True
        environ = {
            "PATH_INFO": "/base/static/src/css/styles.css"
        }

        result = mid.dispatch(environ, start_response)
        assert isinstance(result, MockResponse)

        find_spec.return_value = MockSpec('base', '/test/base')
        exists.return_value = True
        environ = {
            "PATH_INFO": "/base/static/src/css/styles_no_mime"
        }

        result = mid.dispatch(environ, start_response)
        assert isinstance(result, MockResponse)


def test_base_wsgi_app(modules):
    app = MagicMock()

    Custom = type('Custom', (BaseWSGIApp, BaseApp), {})

    http = modules['odoo.http']
    request = http.request
    exceptions = modules['werkzeug.exceptions']
    exceptions.NotFound = MockNotFound

    registry = modules['odoo.modules.registry']

    with patch.dict('sys.modules', modules):
        wsgi = Custom(app)

        # Testing DB routers / Nodb routers
        router = wsgi.get_db_router(False)
        assert router == wsgi.nodb_router.routing_map

        router = wsgi.get_db_router('test')
        assert router == request.registry['ir.http'].routing_map()

        # Test request type related funcnctions
        req_type = wsgi._request_type()
        assert req_type == [Request]

        request = wsgi.get_request(MagicMock())
        assert isinstance(request, wsgi.request_type)

        # Get registry utility
        reg = wsgi.get_registry('test')
        assert reg == registry.Registry('test')

        # Test passthrough get_response as dispatcher
        # handles it properly but odoo needs this :/
        result = MagicMock()
        response = wsgi.get_response(
            request,
            result,
            False
        )
        assert response == result

        # Test CSP
        headers = {
            'Content-Security-Policy': True
        }
        response.headers = headers.copy()
        wsgi.set_csp(response)
        assert response.headers == headers

        # Not setting on regular requests
        response.headers = {}
        wsgi.set_csp(response)
        assert response.headers == {}

        headers = {
            'Content-Type': 'image/png'
        }
        response.headers = headers.copy()
        wsgi.set_csp(response)
        assert response.headers == {
            'Content-Type': 'image/png',
            'Content-Security-Policy': "default-src 'none'",
            'X-Content-Type-Options': 'nosniff',
        }

        # Test match db router
        request = wsgi.get_request(MagicMock())
        request.registry = MagicMock()
        rule = MagicMock()
        request.registry['ir.http']._match.return_value = rule
        router, route = wsgi.match_router(request)
        assert route == rule
        assert router == wsgi.routers[0]

        # Test match nodb router
        request = wsgi.get_request(MagicMock())
        request.registry = MagicMock()
        rule = MagicMock()
        request.registry['ir.http']._match.return_value = None
        router, route = wsgi.match_router(request)
        assert router == wsgi.routers[1]

        # Test no routers

        request = wsgi.get_request(MagicMock())
        request.registry = MagicMock()
        rule = MagicMock()
        request.registry['ir.http']._match.return_value = None
        route = wsgi.nodb_router.routing_map.bind_to_environ(
            request.httprequest.environ
        ).match.side_effect = MockNotFound

        with pytest.raises(DispatcherNotFoundError):
            wsgi.match_router(request)

        # Test dispatchers json
        request = wsgi.get_request(MagicMock())
        request.endpoint = MagicMock()
        request.endpoint.routing = {'type': 'json'}
        dispatcher = wsgi.match_dispatcher(request)
        assert isinstance(dispatcher, JsonRpcDispatcher)

        # Test dispatchers json
        request = wsgi.get_request(MagicMock())
        request.endpoint = MagicMock()
        request.endpoint.routing = {'type': 'plainjson'}
        dispatcher = wsgi.match_dispatcher(request)
        assert isinstance(dispatcher, JsonDispatcher)

        # Test dispatchers html
        request = wsgi.get_request(MagicMock())
        request.endpoint = MagicMock()
        request.endpoint.routing = {'type': 'http'}
        dispatcher = wsgi.match_dispatcher(request)
        assert isinstance(dispatcher, HttpDispatcher)

        # Test dispatchers html
        request = wsgi.get_request(MagicMock())
        request.endpoint = MagicMock()
        request.endpoint.routing = {'type': 'whoa'}
        with pytest.raises(DispatcherNotFoundError):
            wsgi.match_dispatcher(request)


def test_dispatch_basewsgi(modules):
    app = MagicMock()

    class DbMixinRequest(object):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.registry = MagicMock()

    class BaseRegistry(object):
        def _request_type(self):
            req = super()._request_type()
            return [DbMixinRequest] + req

    Custom = type('Custom', (BaseRegistry, BaseWSGIApp, BaseApp), {})

    http = modules['odoo.http']
    request = http.request
    exceptions = modules['werkzeug.exceptions']
    exceptions.NotFound = MockNotFound
    exceptions.HTTPException = MockHTTPException

    wp = modules['werkzeug.wrappers']
    wp.Response = MockResponse

    with patch.dict('sys.modules', modules):
        wsgi = Custom(app)

        environ = {
        }

        def start(status):
            pass

        result = wsgi(environ, start)
        pass
