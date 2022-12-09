import collections
import time
import logging

from .dispatchers import DispatcherNotFoundError

DEFAULT_LANG = 'en_US'


_logger = logging.getLogger(__name__)


class BaseRequestMixin(object):
    def __init__(self, app, httprequest):
        self.app = app


class BaseHTTPRequest(BaseRequestMixin):
    def __init__(self, app, httprequest):
        super().__init__(app, httprequest)
        self.httprequest = httprequest
        self.params = collections.OrderedDict(self.httprequest.args)

        # TODO remove to break test Should be in request dispatcher hmm?
        self.endpoint = None


class BaseRequest(BaseRequestMixin):
    def post_dispatch(self, response):
        pass

    def pre_dispatch(self):
        pass

    def dispatch(self):
        pass

    def get_response(self, result):
        return result
        # return self.dispatcher.get_response(self, result)

    def _handle_exception(self, exception):
        """Called within an except block to allow converting exceptions
           to abitrary responses. Anything returned (except None) will
           be used as response."""
        from odoo.tools import config
        from odoo.tools.debugger import post_mortem
        from odoo.http import NO_POSTMORTEM
        from werkzeug.exceptions import HTTPException
        import sys

        self._failed = exception  # prevent tx commit
        if (
            not isinstance(exception, NO_POSTMORTEM) and
            not isinstance(exception, HTTPException)
        ):
            post_mortem(config, sys.exc_info())

        # WARNING: do not inline or it breaks: raise...from evaluates strictly
        # LTR so would first remove traceback then copy lack of traceback
        new_cause = Exception().with_traceback(exception.__traceback__)
        new_cause.__cause__ = exception.__cause__ or exception.__context__
        # tries to provide good chained tracebacks, just re-raising exception
        # generates a weird message as stacks just get concatenated, exceptions
        # not guaranteed to copy.copy cleanly & we want `exception` as leaf
        # (for # callers to check & look at)
        raise exception.with_traceback(None) from new_cause


class SessionManagementMixin(BaseHTTPRequest):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_session()


    def get_default_session(self):
        return {
            'context': {},
            'db': None,
            'debug': '',
            'login': None,
            'uid': None,
            'session_token': None,
            # profiling
            'profile_session': None,
            'profile_collectors': None,
            'profile_params': None,
        }

    def setup_session(self):
        httprequest = self.httprequest
        # recover or create session
        if self.app.execute_session_gc:
            self.app.session_gc()

        sid = httprequest.args.get('session_id')
        explicit_session = True

        if not sid:
            sid = httprequest.headers.get("X-Openerp-Session-Id")

        if not sid:
            sid = httprequest.cookies.get('session_id')
            explicit_session = False

        if sid is None:
            httprequest.session = self.app.session_store.new()
        else:
            httprequest.session = self.app.session_store.get(sid)

        for key, item in self.get_default_session().items():
            if not hasattr(httprequest.session, key):
                setattr(httprequest.session, key, item)

        # httprequest.session.context['lang'] = self.default_lang()
        httprequest.session.context['lang'] = 'en_US'

        self.explicit_session = explicit_session

    @property
    def __save_session(self):
        return (
            (not self.endpoint) or
            self.endpoint.routing.get('save_session', True)
        )

    def get_response(self, result):
        from odoo.service import security
        response = super().get_response(result)

        httprequest = self.httprequest

        if not self.__save_session:
            return response

        if httprequest.session.should_save:
            if httprequest.session.rotate:
                self.app.session_store.delete(httprequest.session)
                httprequest.session.sid = self.app.session_store.generate_key()
                if httprequest.session.uid:
                    # TODO move env out of here into the DB mixin
                    session_token = security.compute_session_token(
                        httprequest.session, self.env
                    )
                    httprequest.session.session_token = session_token
                httprequest.session.modified = True

            self.app.session_store.save(httprequest.session)

        if not self.explicit_session and hasattr(response, 'set_cookie'):
            response.set_cookie(
                'session_id',
                httprequest.session.sid,
                max_age=90 * 24 * 60 * 60,
                httponly=True
            )

        return response

    def post_dispatch(self, response):
        super().post_dispatch(response)

    def pre_dispatch(self):
        super().pre_dispatch()


class WebManagementMixin(BaseRequestMixin):
    def handle_redirect_location(self, location, code=303, local=True):
        from werkzeug.urls import URL, url_parse

        if isinstance(location, URL):
            location = location.to_url()

        if local:
            location = '/{}'.format(
                url_parse(location)
                .replace(scheme='', netloc='')
                .to_url()
                .lstrip('/')
            )

        return location

    def not_found(self, description=None):
        """ Shortcut for a `HTTP 404
        <http://tools.ietf.org/html/rfc7231#section-6.5.4>`_ (Not Found)
        response
        """
        from werkzeug.exceptions import NotFound
        return NotFound(description)

    def redirect(self, location, code=303, local=True):
        from werkzeug.wrappers import Response
        from werkzeug.utils import redirect
        location = self.handle_redirect_location(location, code, local)
        return redirect(location, code, Response=Response)

    def redirect_query(self, location, query=None, code=303, local=True):
        from werkzeug.urls import url_encode
        if query:
            location += '?' + url_encode(query)
        return self.redirect(location, code=code, local=local)

    @property
    def session(self):
        return self.httprequest.session


class DbManagementMixin(
    WebManagementMixin,
    SessionManagementMixin,
    BaseRequest,
):
    def __init__(self, app, httprequest):
        from odoo.api import Environment
        super().__init__(app, httprequest)
        self.set_defaults()

        self.uid = httprequest.session.uid

        if self.httprequest.session.db:
            self._env = Environment(self.cr, self.uid, self.session.context)

    def set_defaults(self):
        self._registry = None
        self._env = None
        self._uid = None
        self._cr = None
        self._lang = None

    def redirect(self, location, code=303, local=True):
        if self.db:
            location = self.handle_redirect_location(location, code, local)
            return self.env['ir.http']._redirect(location, code)
        else:
            return super().redirect(location, code, local)

    # def get_response(self, result):
    #     from odoo.http import Response

    #     result = super().get_response(result)

    #     # if isinstance(result, Response) and result.is_qweb:
    #     #     try:
    #     #         result.flatten()
    #     #     except Exception as e:
    #     #         if self.db:
    #     #             result = self.registry['ir.http']._handle_exception(e)
    #     #         else:
    #     #             raise

    #     return result

    # def pre_dispatch(self):
    #     super().pre_dispatch(self)
    #     if self.httprequest.session.db:
    #         self.registry['ir.http']._pre_dispatch(self.rule, self.args)

    def post_dispatch(self, response):
        super().post_dispatch(response)
        if self.httprequest.session.db:
            self.registry['ir.http']._post_dispatch(response)

            self.cr.commit()
            self.cr.close()
            self.cr = None

    def dispatch(self):
        from werkzeug.exceptions import NotFound
        # from contextlib import closing
        # from odoo.api import Environment, SUPERUSER_ID
        # from odoo.http import Response

        if self.httprequest.session.db:

            # Called to force some things to be configured
            # TODO remove
            self.registry['ir.http']._dispatch()

            try:
                result = super().dispatch()
            except DispatcherNotFoundError:
                return NotFound()

            return result
        else:
            return super().dispatch()

    def update_env(self, user=None, context=None, su=None):
        import threading
        self._env = self._env(None, user, context, su)
        threading.current_thread().uid = self.env.uid

    def update_context(self, **overrides):
        self.update_env(context=dict(self.env.context, **overrides))

    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, lang):
        self._lang = lang

    @property
    def website(self):
        return self.env['website'].browse(self.website_routing)

    @website.setter
    def website(self, val):
        _logger.warning("Setting website is deprecated")

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self, val):
        self._uid = val
        if self._env:
            self.update_env(user=val)

    @property
    def registry(self):
        if not self.db:
            raise RuntimeError("Should not happen")

        return self.app.get_registry(self.db)

        from odoo.modules.registry import Registry
        if self._registry is None:
            self._registry = Registry.new(self.session.db)
        return self._registry

    @property
    def cr(self):
        if self._cr is None:
            self._cr = self.registry.cursor()

        return self._cr

    @cr.setter
    def cr(self, val):
        self._cr = val
        self._env = None

    @property
    def env(self):
        from odoo.api import Environment

        if self._env is None:
            self._env = Environment(self.cr, self.uid, self.session.context)

        return self._env

    @property
    def context(self):
        return self.env.context

    # lunch app
    @property
    def _context(self):
        return self.env.context

    @context.setter
    def context(self, val):
        self.update_context(**val)

    @property
    def db(self):
        return self.httprequest.session.db

    def pre_dispatch(self):
        from odoo.http import db_filter, db_monodb

        super().pre_dispatch()

        if 'db' in self.httprequest.args:
            self.httprequest.session.db = self.httprequest.args['db']

        db = self.httprequest.session.db

        # Check if session.db is legit
        if db:
            if db not in db_filter([db], httprequest=self.httprequest):
                _logger.warning(
                    (
                        "Logged into database '%s', but dbfilter "
                        "rejects it; logging session out."
                    ),
                    db
                )
                self.httprequest.session.logout()
                db = None

        if not db:
            self.httprequest.session.db = db_monodb(self.httprequest)

    def _is_cors_preflight(self, endpoint):
        return False


class RequestDispatcher(BaseHTTPRequest):
    def __init__(self, app, httprequest):
        super().__init__(app, httprequest)
        self.endpoint = None
        self.route = None
        self.dispatcher = None
        self.args = None

    def get_http_params(self):
        """
        Extract key=value pairs from the query string and the forms
        present in the body (both application/x-www-form-urlencoded and
        multipart/form-data).
        :returns: The merged key-value pairs.
        :rtype: dict
        """
        params = {
            **self.httprequest.args,
            **self.httprequest.form,
            **self.httprequest.files
        }
        params.pop('session_id', None)
        return params

    def dispatch(self):
        return self.dispatcher.dispatch(self)

    @property
    def endpoint_arguments(self):
        return self.args


class ResponseMaker(BaseRequestMixin):
    def make_response(self, data, headers=None, cookies=None, status=200):
        """ Helper for non-HTML responses, or HTML responses with custom
        response headers or cookies.
        While handlers can just return the HTML markup of a page they want to
        send as a string if non-HTML data is returned they need to create a
        complete response object, or the returned data will not be correctly
        interpreted by the clients.
        :param str data: response body
        :param int status: http status code
        :param headers: HTTP headers to set on the response
        :type headers: ``[(name, value)]``
        :param collections.abc.Mapping cookies: cookies to set on the client
        :returns: a response object.
        :rtype: :class:`~odoo.http.Response`
        """
        from odoo.http import Response
        response = Response(data, status=status, headers=headers)
        if cookies:
            for k, v in cookies.items():
                response.set_cookie(k, v)
        return response

    def make_json_response(self, data, headers=None, cookies=None, status=200):
        """ Helper for JSON responses, it json-serializes ``data`` and
        sets the Content-Type header accordingly if none is provided.
        :param data: the data that will be json-serialized into the response
                     body
        :param int status: http status code
        :param List[(str, str)] headers: HTTP headers to set on the response
        :param collections.abc.Mapping cookies: cookies to set on the client
        :rtype: :class:`~odoo.http.Response`
        """
        import werkzeug
        import json
        import date_utils
        data = json.dumps(
            data, ensure_ascii=False, default=date_utils.json_default
        )

        headers = werkzeug.datastructures.Headers(headers)
        headers['Content-Length'] = len(data)
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json; charset=utf-8'

        return self.make_response(
            data, headers.to_wsgi_list(), cookies, status
        )


class Request(
    WebManagementMixin,
    # SessionManagementMixin,
    ResponseMaker,
    RequestDispatcher,
    BaseHTTPRequest,
    BaseRequest,
):
    def __init__(self, app, httprequest):
        super().__init__(app, httprequest)
        # self.app = app
        self.rule = None
        self.endpoint = None

    def render(self, template, qcontext=None, lazy=True, **kw):
        from odoo.http import Response
        """ Lazy render of a QWeb template.
        The actual rendering of the given template will occur at then end of
        the dispatching. Meanwhile, the template and/or qcontext can be
        altered or even replaced by a static response.
        :param basestring template: template to render
        :param dict qcontext: Rendering context to use
        :param bool lazy: whether the template rendering should be deferred
                          until the last possible moment
        :param kw: forwarded to werkzeug's Response object
        """
        response = Response(template=template, qcontext=qcontext, **kw)
        if not lazy:
            return response.render()
        return response

    def csrf_token(self, time_limit=None):
        """ Generates and returns a CSRF token for the current session
        :param time_limit: the CSRF token validity period (in seconds), or
                           ``None`` for the token to be valid as long as the
                           current user session is (the default)
        :type time_limit: int | None
        :returns: ASCII token string
        """
        import time
        import hmac
        import hashlib
        token = self.session.sid

        # if no `time_limit` => distant 1y expiry (31536000)
        # so max_ts acts as salt, e.g. vs BREACH
        max_ts = int(time.time() + (time_limit or 31536000))

        msg = '%s%s' % (token, max_ts)
        secret = self.env['ir.config_parameter'].sudo().get_param(
            'database.secret'
        )
        assert secret, "CSRF protection requires a configured database secret"
        hm = hmac.new(
            secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1
        ).hexdigest()
        return '%so%s' % (hm, max_ts)

    def validate_csrf(self, csrf):
        import hmac
        from odoo.tools import consteq
        import hashlib

        if not csrf:
            return False

        try:
            hm, _, max_ts = str(csrf).rpartition('o')
        except UnicodeEncodeError:
            return False

        if max_ts:
            try:
                if int(max_ts) < int(time.time()):
                    return False
            except ValueError:
                return False

        token = self.session.sid

        msg = '%s%s' % (token, max_ts)
        secret = self.env['ir.config_parameter'].sudo().get_param(
            'database.secret'
        )
        assert secret, "CSRF protection requires a configured database secret"
        hm_expected = hmac.new(
            secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1
        ).hexdigest()
        return consteq(hm, hm_expected)

    def default_lang(self):
        """Returns default user language according to request specification
        :returns: Preferred language if specified or 'en_US'
        :rtype: str
        """
        import babel
        lang = self.httprequest.accept_languages.best
        if not lang:
            return DEFAULT_LANG

        try:
            code, territory, _, _ = babel.core.parse_locale(lang, sep='-')
            if territory:
                lang = f'{code}_{territory}'
            else:
                lang = babel.core.LOCALE_ALIASES[code]
            return lang
        except (ValueError, KeyError):
            return DEFAULT_LANG
