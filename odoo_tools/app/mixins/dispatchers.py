import logging

_logger = logging.getLogger(__name__)


class DispatcherNotFoundError(Exception):
    def __init__(self, message, httprequest):
        super().__init__(message)
        self.request = httprequest


class BaseRequestDispatcher(object):
    def __init__(self, app):
        self.app = app

    def handle_exception(self, request, exception):
        from odoo.http import Response
        return Response("Something went wrong", status=500)

    def handle_result(self, request, result):
        from odoo.http import Response

        if isinstance(result, Response) and result.is_qweb:
            result.flatten()

        return result

    def format_response(self, request, result):
        from odoo.http import Response

        if isinstance(result, (bytes, str)):
            response = Response(result, mimetype='text/html')
        else:
            response = result

        if isinstance(response, Response):
            self.app.set_csp(response)

        return response

    def dispatch(self, request):
        from werkzeug.exceptions import HTTPException
        self.apply_params(request)

        try:
            result = request.endpoint(**request.params)
            result = self.handle_result(request, result)
        except HTTPException:
            raise
        except Exception as exception:
            _logger.error("Error while dispatching", exc_info=True)
            result = self.handle_exception(request, exception)

        return self.format_response(request, result)


class JsonDispatcher(BaseRequestDispatcher):
    def accept(self, request):
        return request.endpoint.routing['type'] == 'plainjson'

    def handle_result(self, request, response):
        return self.format_json(response, 200)

    def handle_exception(self, request, exception):
        response = {
            "error": str(exception)
        }

        return self.format_json(response, status=500)

    def apply_json_request(self, request):
        import json
        import werkzeug

        data = request.httprequest.get_data().decode(
            request.httprequest.charset
        )

        try:
            request.jsonrequest = json.loads(data)
        except ValueError:
            msg = "Invalid JSON DATA: {data}"
            raise werkzeug.exceptions.BadRequest(msg)

    def apply_params(self, request):
        if request.httprequest.method != 'GET':
            self.apply_json_request(request)
        request.params = dict(request.args)

    def format_json(self, data, status=200, headers=None):
        import json
        from odoo.http import Response
        from odoo.tools import date_utils

        data = json.dumps(data, default=date_utils.json_default)

        new_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', len(data)),
        ]

        if headers:
            for header in headers:
                new_headers.append(header)

        return Response(data, status=status, headers=new_headers)


class JsonRpcDispatcher(JsonDispatcher):

    def accept(self, request):
        return request.endpoint.routing['type'] == 'json'

    def apply_params(self, request):
        super().apply_params(request)
        request.params = dict(request.jsonrequest.get("params", {}))

    def rpc_response(self, request, result):
        response = {
            'jsonrpc': '2.0',
            'id': request.jsonrequest.get('id'),
        }

        response.update(result)

        return response

    def handle_exception(self, request, exception):
        from odoo.http import serialize_exception

        error = {
            'code': 200,
            'message': 'Odoo Server Error',
            'data': serialize_exception(exception)
        }

        data = {'error': error}

        response = self.rpc_response(request, data)
        return self.format_json(response, 200)

    def handle_result(self, request, result):
        value = {}
        if result is not None:
            value['result'] = result

        response = self.rpc_response(request, value)
        return self.format_json(response, status=200)


class HttpDispatcher(BaseRequestDispatcher):
    routing_type = 'http'

    def accept(self, request):
        return request.endpoint.routing['type'] == 'http'

    def apply_params(self, request):
        request.params = dict(request.get_http_params(), **request.args)

    def post_dispatch(self, response):
        pass
