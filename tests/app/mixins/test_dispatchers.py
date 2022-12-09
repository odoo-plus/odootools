import json
import pytest
from mock import MagicMock, patch
from odoo_tools.app.mixins.dispatchers import (
    DispatcherNotFoundError,
    BaseRequestDispatcher,
    JsonDispatcher,
    JsonRpcDispatcher,
    HttpDispatcher
)


class MockBadRequest(Exception):
    pass


class MockResponse(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class MockException(Exception):
    pass


@pytest.fixture
def dispatcher():
    app = MagicMock()

    dispatcher = BaseRequestDispatcher(app)

    return dispatcher


@pytest.fixture()
def modules():
    return {
        "odoo": MagicMock(),
        "odoo.http": MagicMock(),
        "odoo.tools": MagicMock(),
        "werkzeug": MagicMock(),
        "werkzeug.exceptions": MagicMock()
    }


def test_dispatcher_not_found():

    message = "error not found"
    request = MagicMock()

    error = DispatcherNotFoundError(message, request)

    assert error.args[0] == message
    assert error.request == request


def test_base_dispatcher_handle_exception(dispatcher, modules):
    http_mock = modules['odoo.http']

    with patch.dict('sys.modules', modules):
        request = MagicMock()
        exception = MagicMock()

        response = dispatcher.handle_exception(request, exception)

        http_mock.Response.assert_called_once_with(
            'Something went wrong',
            status=500
        )

        assert response._mock_new_parent == http_mock.Response


def test_base_dispatcher_handle_result(dispatcher, modules):
    http_mock = modules['odoo.http']

    response_type = type('Response', (object,), {})

    http_mock.Response = response_type

    with patch.dict('sys.modules', modules):
        request = MagicMock()
        result1 = MagicMock()

        result = dispatcher.handle_result(request, result1)

        result1.flatten.assert_not_called()
        assert result == result1

        result2 = response_type()
        result2.is_qweb = False
        result2.flatten = MagicMock()

        result3 = dispatcher.handle_result(request, result2)
        result3.flatten.assert_not_called()
        assert result3 == result2

        result2.is_qweb = True
        result3 = dispatcher.handle_result(request, result2)
        result3.flatten.assert_called_once()


def test_base_dispatcher_format_response(dispatcher, modules):
    http_mock = modules['odoo.http']

    http_mock.Response = MockResponse

    with patch.dict('sys.modules', modules):
        result1 = MockResponse()
        request = MagicMock()

        result2 = dispatcher.format_response(request, result1)

        assert result1 == result2

        dispatcher.app.set_csp.assert_called_once()

        result3 = "data"
        result4 = dispatcher.format_response(request, result3)

        assert result3 != result4
        assert isinstance(result4, MockResponse)
        assert result4.args[0] == result3


def test_base_dispatcher_dispatch(dispatcher, modules):
    with patch.dict('sys.modules', modules):
        with pytest.raises(AttributeError):
            dispatcher.dispatch(MagicMock())

    class CustomDispatcher(BaseRequestDispatcher):

        def apply_params(self, request):
            request.params = request.custom_params
            request.endpoint = MagicMock()
            request.endpoint.return_value = "hello"

    class FailDispatcher(BaseRequestDispatcher):
        def apply_params(self, request):
            request.endpoint = MagicMock()
            request.endpoint.side_effect = MockException("hey", request)
            request.params = {}

    app = MagicMock()

    dispatcher = CustomDispatcher(app)
    fail_dispatcher = FailDispatcher(app)

    http_mock = modules['odoo.http']
    http_mock.Response = MockResponse

    wk_exception = modules['werkzeug.exceptions']
    wk_exception.HTTPException = MockException

    with patch.dict('sys.modules', modules):
        request = MagicMock()
        request.custom_params = {"a": "b"}
        response = dispatcher.dispatch(request)
        assert isinstance(response, MockResponse)
        assert response.args[0] == "hello"

        request = MagicMock()
        # Cannot parse list in params will raise exception
        request.custom_params = []
        response = dispatcher.dispatch(request)
        assert isinstance(response, MockResponse)
        assert response.kwargs['status'] == 500
        assert response.args[0] == 'Something went wrong'

        with pytest.raises(MockException):
            request = MagicMock()
            response = fail_dispatcher.dispatch(request)


def test_json_dispatcher(modules):
    app = MagicMock()
    dispatcher = JsonDispatcher(app)

    http_mock = modules['odoo.http']
    http_mock.Response = MockResponse

    wk_exc = modules['werkzeug']
    wk_exc.exceptions.BadRequest = MockBadRequest

    with patch.dict('sys.modules', modules):
        request = MagicMock()
        request.endpoint = MagicMock()

        request.endpoint.routing = {'type': 'plainjson'}
        result = dispatcher.accept(request)
        assert result is True

        request.endpoint.routing = {'type': 'json'}
        result = dispatcher.accept(request)
        assert result is False

        data = {"a": 1}

        result = dispatcher.format_json(
            data,
            status=202,
            headers=[('OH', 'A')]
        )

        assert result.args[0] == '{"a": 1}'
        assert result.kwargs['status'] == 202
        assert result.kwargs['headers'] == [
            ('Content-Type', 'application/json'),
            ('Content-Length', len(result.args[0])),
            ('OH', 'A')
        ]

        result = dispatcher.handle_result(request, data)
        assert result.args[0] == '{"a": 1}'
        assert result.kwargs['status'] == 200
        assert result.kwargs['headers'] == [
            ('Content-Type', 'application/json'),
            ('Content-Length', len(result.args[0])),
        ]

        result = dispatcher.handle_exception(request, Exception("blop"))
        assert result.args[0] == '{"error": "blop"}'

        request = MagicMock()
        request.httprequest.charset = 'utf-8'
        request.httprequest.get_data.return_value = b'{"a": true, "b": 1}'
        dispatcher.apply_json_request(request)
        assert request.jsonrequest == {"a": True, "b": 1}

        request = MagicMock()
        request.httprequest.charset = 'utf-8'
        request.httprequest.get_data.return_value = b'{"a": true, "b": 1}'
        request.args = {"b": "c"}
        dispatcher.apply_json_request(request)
        dispatcher.apply_params(request)
        assert request.params == {"b": "c"}
        assert request.jsonrequest == {"a": True, "b": 1}

        request = MagicMock()
        request.httprequest.charset = 'utf-8'
        request.httprequest.get_data.return_value = b'{"a": true, "b": 1'

        with pytest.raises(MockBadRequest):
            dispatcher.apply_json_request(request)


def test_jsonrpc_dispatcher(modules):
    app = MagicMock()
    dispatcher = JsonRpcDispatcher(app)

    http_mock = modules['odoo.http']
    http_mock.Response = MockResponse
    http_mock.serialize_exception = lambda exc: str(exc)

    with patch.dict('sys.modules', modules):
        request = MagicMock()
        result = dispatcher.accept(request)
        assert result is False

        request.endpoint.routing = {'type': 'json'}
        result = dispatcher.accept(request)
        assert result is True

        request = MagicMock()
        request.httprequest.charset = 'utf-8'

        rpc_data = b'{"jsonrpc": "2.0", "id": 1, "params": {"a": 1}}'
        result_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "params": {
                "a": 1
            }
        }
        request.httprequest.get_data.return_value = rpc_data
        dispatcher.apply_params(request)
        result = dispatcher.rpc_response(request, {"result": {"ok": True}})
        assert request.jsonrequest == result_data
        assert request.params == {"a": 1}
        assert result == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "ok": True
            }
        }

        result = dispatcher.handle_result(request, {"ok": True})
        assert json.loads(result.args[0]) == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "ok": True
            }
        }

        result = dispatcher.handle_exception(request, Exception("whoa"))
        assert json.loads(result.args[0]) == {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
              'code': 200,
              'message': 'Odoo Server Error',
              'data': "whoa",
            }
        }


def test_http_dispatcher(modules):
    app = MagicMock()

    dispatcher = HttpDispatcher(app)

    with patch.dict('sys.modules', modules):
        request = MagicMock()
        request.endpoint.routing = {'type': 'json'}
        result = dispatcher.accept(request)
        assert result is False

        request.endpoint.routing = {'type': 'http'}
        result = dispatcher.accept(request)
        assert result is True

        request.get_http_params = lambda: {"a": 1}
        request.args = {"b": 2}
        result = dispatcher.apply_params(request)
        assert request.params == {"a": 1, "b": 2}

        dispatcher.post_dispatch("wh")
