import importlib
from importlib.util import find_spec
import logging
from pathlib import Path

from . import dispatchers
from .dispatchers import DispatcherNotFoundError
from . import routers

from .request import (
    Request,
)

_logger = logging.getLogger(__name__)


class AssetsMiddleware(object):
    def get_assets_path(self, path_info):
        module, part, path = path_info[1:].partition('/static/')

        if part != '/static/':
            return

        try:
            spec = find_spec(f"odoo.addons.{module}")
            if not spec:
                return
        except ModuleNotFoundError:
            return

        module_path = spec.submodule_search_locations[0]
        file_path = Path(module_path) / 'static' / path
        if not file_path.exists():
            return

        return file_path


class StaticAssetsMiddleware(AssetsMiddleware):
    def __init__(self, application):
        super().__init__(application)

    def dispatch(self, environ, start_response):
        module, part, path = environ['PATH_INFO'][1:].partition('/static/')

        if part != '/static/':
            return super().dispatch(environ, start_response)

        try:
            spec = find_spec(f"odoo.addons.{module}")
            if not spec:
                return super().dispatch(environ, start_response)
        except ModuleNotFoundError:
            return super().dispatch(environ, start_response)

        # from odoo.http import Response
        from werkzeug.wrappers import Response
        from mimetypes import guess_type

        module_path = spec.submodule_search_locations[0]

        file_path = Path(module_path) / 'static' / path

        if not file_path.exists():
            return super().dispatch(environ, start_response)

        mime = guess_type(path)[0] or 'application/octet-stream'

        headers = []

        headers.append(('Content-Type', mime))

        data = file_path.open('rb')

        response = Response(data, headers=headers)

        return response(environ, start_response)


class AddonsLoaderMiddleware(object):
    def __init__(self, application):
        super().__init__(application)

        self.load_addons_manifest()

    def load_addons_manifest(self):
        from odoo.http import addons_manifest
        from odoo import addons

        # from odoo.modules.module import read_manifest
        from odoo.modules.module import load_information_from_description_file

        import os
        # from os.path import join as opj

        manifests = addons_manifest

        skipped_module = []
        skipped_manifest = []

        for addons_path in addons.__path__:
            for module in sorted(os.listdir(str(addons_path))):
                if module in manifests:
                    skipped_module.append(module)
                    continue

                # Deal with the manifest first
                # mod_path = opj(addons_path, module)
                manifest = load_information_from_description_file(module)
                # manifest = read_manifest(addons_path, module)
                if (
                    not manifest or
                    (
                        not manifest.get('installable', True) and
                        'assets' not in manifest
                    )
                ):
                    skipped_manifest.append(module)
                    continue

                manifest['addons_path'] = addons_path
                manifests[module] = manifest


class BaseApp(object):
    def __init__(self, application):
        super().__init__()


class BaseWSGIApp(object):
    def __init__(self, application):
        super().__init__(application)

        self.app = application
        self._loaded = True

        self.dispatchers = [
            dispatchers.JsonDispatcher(self),
            dispatchers.JsonRpcDispatcher(self),
            dispatchers.HttpDispatcher(self),
        ]

        self.nodb_router = routers.NodbRouter(self)

        self.routers = [
            routers.DbRouter(self),
            self.nodb_router,
        ]

        # TODO compute at init time
        self.request_type = self.build_request_type()

        self.registries = {}

    def get_db_router(self, db):
        from odoo.http import request

        if not db:
            return self.nodb_router.routing_map

        return request.registry['ir.http'].routing_map()

    def get_registry(self, name):
        from odoo.modules.registry import Registry
        return Registry(name)
        # if name in self.registries:
        #     return self.registries[name]

        # registry = Registry.new(name)
        # self.registries[name] = registry

        # return registry

    def _request_type(self):
        return [Request]

    def __call__(self, environ, start_response):
        return self.dispatch(environ, start_response)

    def match_router(self, request):
        from werkzeug.exceptions import NotFound

        for router in self.routers:
            try:
                route = router.match(request)
                if route:
                    break
            except NotFound:
                pass
        else:
            raise DispatcherNotFoundError(
                "Couldn't find a proper router for request.", self
            )

        return router, route

    def match_dispatcher(self, request):
        for dispatcher in self.dispatchers:
            if dispatcher.accept(request):
                break
        else:
            raise DispatcherNotFoundError(
                "Dispatcher not found", request.httprequest
            )

        return dispatcher

    def dispatch(self, environ, start_response):
        # from werkzeug.exceptions import NotFound
        import werkzeug
        from odoo.tools._vendor.useragents import UserAgent
        from odoo.http import _request_stack
        from werkzeug.exceptions import HTTPException
        from werkzeug.datastructures import ImmutableOrderedMultiDict

        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.user_agent_class = UserAgent
        httprequest.parameter_storage_class = ImmutableOrderedMultiDict

        request = self.get_request(httprequest)
        _request_stack.push(request)
        self.request = request
        router = None
        response = None

        try:
            router, route = self.match_router(request)
            router.apply_router(request, router, route)
            request.dispatcher = self.match_dispatcher(request)

            request.pre_dispatch()
            response = request.get_response(request.dispatch())
        except HTTPException as error:
            response = request.get_response(error.response)
        except Exception as exc:
            _logger.error(
                "Something happened while dispatching", exc_info=True
            )

            if not router:
                routers = self.routers
            else:
                routers = [router]

            for router in routers:
                response = router.serve_fallback(request, exc)
                if response:
                    break

            response = request.get_response(response)
        finally:
            request.post_dispatch(response)
            _request_stack.pop()
            self.request = None

        _logger.info(
            f"{request.httprequest.path} {request.httprequest.method}"
        )

        return response(environ, start_response)

    def build_request_type(self):
        req_bases = self._request_type()
        request_type = type('Request', tuple(req_bases), {})
        return request_type

    def get_request(self, httprequest):
        return self.request_type(self, httprequest)

    def set_csp(self, response):
        headers = response.headers
        if 'Content-Security-Policy' in headers:
            return

        import cgi
        mime, _params = cgi.parse_header(headers.get('Content-Type', ''))
        if not mime.startswith('image/'):
            return

        headers['Content-Security-Policy'] = "default-src 'none'"
        headers['X-Content-Type-Options'] = 'nosniff'

    def get_response(self, httprequest, result, explicit_session):
        return result
