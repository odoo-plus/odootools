from .routing import _generate_routing_rules, ROUTING_KEYS, submap


class BaseRouter(object):
    def __init__(self, application):
        self.app = application

    @classmethod
    def match(self, request):
        raise NotImplementedError()

    def apply_router(self, request, router, route):
        request.router = router
        request.rule = route[0]
        request.endpoint = request.rule.endpoint
        request.args = route[1]

    def serve_fallback(self, request, exception):
        from werkzeug.exceptions import NotFound
        return NotFound(description="Url couldn't be located")


class DbRouter(BaseRouter):
    def match(self, request):
        if not request.session.db:
            return False

        ir_http = request.registry['ir.http']

        ir_http._handle_debug()

        # TODO set in a better place? should have http_routing loaded
        # but not all db may have it loaded.
        # request.lang = ir_http._get_default_lang()

        rule = ir_http._match(request.httprequest.path)

        return rule

    def apply_router(self, request, router, route):
        super().apply_router(request, router, route)

        ir_http = request.registry['ir.http']
        ir_http._postprocess_args(request.args, request.rule)

    def serve_fallback(self, request, exception):
        from werkzeug.wrappers import Response

        if not request.session.db:
            return super().serve_fallback(request, exception)

        ir_http = request.registry['ir.http']
        response = ir_http._serve_fallback(exception)

        if isinstance(response, Response) and response.is_qweb:
            response.flatten()

        return response


class NodbRouter(BaseRouter):

    def match(self, request):
        routes = self.routing_map
        router = routes.bind_to_environ(request.httprequest.environ)
        return router.match(return_rule=True)

    @property
    def routing_map(self):
        import odoo
        import werkzeug

        nodb_routing_map = werkzeug.routing.Map(
            strict_slashes=False, converters=None
        )

        modules = [''] + odoo.conf.server_wide_modules

        for url, endpoint in _generate_routing_rules(modules, nodb_only=True):
            routing = submap(endpoint.routing, ROUTING_KEYS)
            if (
                routing['methods'] is not None and
                'OPTIONS' not in routing['methods']
            ):
                routing['methods'] = routing['methods'] + ['OPTIONS']
            rule = werkzeug.routing.Rule(url, endpoint=endpoint, **routing)
            rule.merge_slashes = False
            nodb_routing_map.add(rule)

        return nodb_routing_map
