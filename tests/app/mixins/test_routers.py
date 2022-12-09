import pytest
from mock import MagicMock, patch
from odoo_tools.app.mixins.routers import (
    BaseRouter,
    DbRouter,
    NodbRouter
)


class MockMap(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.rules = []
        self.return_rule = None

    def bind_to_environ(self, environ):
        self.environ = environ
        return self

    def add(self, rule):
        self.rules.append(rule)

    def match(self, return_rule=False):
        self.return_rule = return_rule
        if self.rules:
            return self.rules[0]


class MockRule(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class MockResponse(object):
    def __init__(self, is_qweb):
        self.flatten = MagicMock()
        self.is_qweb = is_qweb


class MockNotFound(Exception):
    def __init__(self, description):
        super().__init__(description)


@pytest.fixture
def modules():
    return {
        "odoo": MagicMock(),
        "odoo.http": MagicMock(),
        "werkzeug": MagicMock(),
        "werkzeug.exceptions": MagicMock(),
        "werkzeug.wrappers": MagicMock(),
        "werkzeug.routing": MagicMock()
    }


def test_base_router(modules):
    app = MagicMock()
    brouter = BaseRouter(app)

    assert app == brouter.app

    with pytest.raises(NotImplementedError):
        request = MagicMock()
        BaseRouter.match(request)

    request = MagicMock()
    router = MagicMock()
    route = [MagicMock(), MagicMock()]
    endpoint = route[0].endpoint
    brouter.apply_router(
        request, router, route
    )

    assert request.args == route[1]
    assert request.rule == route[0]
    assert request.router == router
    assert request.endpoint == endpoint

    wk_exc = modules['werkzeug.exceptions']
    wk_exc.NotFound = MockNotFound

    with patch.dict('sys.modules', modules):
        result = brouter.serve_fallback(request, Exception("whoa"))
        assert isinstance(result, MockNotFound)


def test_db_router(modules):
    app = MagicMock()
    brouter = DbRouter(app)

    wk_exc = modules['werkzeug.exceptions']
    wk_exc.NotFound = MockNotFound

    wk_wrp = modules['werkzeug.wrappers']
    wk_wrp.Response = MockResponse

    registry = {
        'ir.http': MagicMock()
    }

    ir_http = registry['ir.http']
    ir_http._get_default_lang.return_value = 'fr_CA'
    rule = (MagicMock(), MagicMock())
    ir_http._match.return_value = rule
    postproc = ir_http._postprocess_args
    ir_http._serve_fallback = lambda exc: exc

    request = MagicMock()
    request.registry = registry

    assert brouter.match(request) == rule

    request.session.db = False

    assert brouter.match(request) is False

    postproc.assert_not_called()

    router = MagicMock()
    route = [MagicMock(), MagicMock()]
    endpoint = route[0].endpoint

    brouter.apply_router(request, router, route)

    assert request.args == route[1]
    assert request.rule == route[0]
    assert request.router == router
    assert request.endpoint == endpoint

    postproc.assert_called_once_with(request.args, request.rule)

    with patch.dict('sys.modules', modules):
        result = brouter.serve_fallback(request, Exception("whoa"))
        assert isinstance(result, MockNotFound)

        request.session.db = 'test'

        result = brouter.serve_fallback(request, Exception("whoa"))
        assert isinstance(result, Exception)

        result = brouter.serve_fallback(request, "whoa")
        assert result == "whoa"

        result = brouter.serve_fallback(request, MockResponse(is_qweb=False))
        result.flatten.assert_not_called()

        result = brouter.serve_fallback(request, MockResponse(is_qweb=True))
        result.flatten.assert_called_once()


def test_nodb_router(modules):
    app = MagicMock()
    brouter = NodbRouter(app)

    request = MagicMock()

    wk = modules['werkzeug']
    wk.routing.Map = MockMap
    wk.routing.Rule = MockRule

    gen_rule = 'odoo_tools.app.mixins.routers._generate_routing_rules'

    with patch.dict('sys.modules', modules), \
         patch(gen_rule) as rules:
        endpoint = MagicMock()
        endpoint.routing = {
            "methods": ["GET"]
        }
        rules.return_value = [('/fun', endpoint)]
        result = brouter.match(request)
        assert isinstance(result, MockRule)
        assert result.args[0] == '/fun'
        assert result.kwargs['endpoint'] == endpoint
