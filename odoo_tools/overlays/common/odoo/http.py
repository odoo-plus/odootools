if '_logger' not in globals():
    _logger = None
    werkzeug = None
    Response = None
    inspect = None
    functools = None


def route(route=None, **kw):
    """Decorator marking the decorated method as being a handler for
    requests. The method must be part of a subclass of ``Controller``.
    :param route: string or array. The route part that will determine which
                  http requests will match the decorated method. Can be a
                  single string or an array of strings. See werkzeug's routing
                  documentation for the format of route expression (
                  http://werkzeug.pocoo.org/docs/routing/ ).
    :param type: The type of request, can be ``'http'`` or ``'json'``.
    :param auth: The type of authentication method, can on of the following:
                 * ``user``: The user must be authenticated and the current
                   request
                   will perform using the rights of the user.
                 * ``public``: The user may or may not be authenticated. If
                   she isn't, the current request will perform using the shared
                   Public user.
                 * ``none``: The method is always active, even if there is no
                   database. Mainly used by the framework and authentication
                   modules. There request code will not have any facilities to
                   access the database nor have any configuration indicating
                   the current database nor the current user.
    :param methods: A sequence of http methods this route applies to. If not
                    specified, all methods are allowed.
    :param cors: The Access-Control-Allow-Origin cors directive value.
    :param bool csrf: Whether CSRF protection should be enabled for the route.
                      Defaults to ``True``. See :ref:`CSRF Protection
                      <csrf>` for more.
    .. _csrf:
    .. admonition:: CSRF Protection
        :class: alert-warning
        .. versionadded:: 9.0
        Odoo implements token-based `CSRF protection
        <https://en.wikipedia.org/wiki/CSRF>`_.
        CSRF protection is enabled by default and applies to *UNSAFE*
        HTTP methods as defined by :rfc:`7231` (all methods other than
        ``GET``, ``HEAD``, ``TRACE`` and ``OPTIONS``).
        CSRF protection is implemented by checking requests using
        unsafe methods for a value called ``csrf_token`` as part of
        the request's form data. That value is removed from the form
        as part of the validation and does not have to be taken in
        account by your own form processing.
        When adding a new controller for an unsafe method (mostly POST
        for e.g. forms):
        * if the form is generated in Python, a csrf token is
          available via :meth:`request.csrf_token()
          <odoo.http.WebRequest.csrf_token`, the
          :data:`~odoo.http.request` object is available by default
          in QWeb (python) templates, it may have to be added
          explicitly if you are not using QWeb.
        * if the form is generated in Javascript, the CSRF token is
          added by default to the QWeb (js) rendering context as
          ``csrf_token`` and is otherwise available as ``csrf_token``
          on the ``web.core`` module:
          .. code-block:: javascript
              require('web.core').csrf_token
        * if the endpoint can be called by external parties (not from
          Odoo) as e.g. it is a REST API or a `webhook
          <https://en.wikipedia.org/wiki/Webhook>`_, CSRF protection
          must be disabled on the endpoint. If possible, you may want
          to implement other methods of request validation (to ensure
          it is not called by an unrelated third-party).
    """
    routing = kw.copy()
    # assert 'type' not in routing or routing['type'] in ("http", "json")

    def decorator(f):
        if route:
            if isinstance(route, list):
                routes = route
            else:
                routes = [route]
            routing['routes'] = routes
            wrong = routing.pop('method', None)
            if wrong:
                kw.setdefault('methods', wrong)

                msg = (
                    "<function %s.%s> defined with invalid routing parameter "
                    "'method', assuming 'methods'"
                )

                _logger.warning(
                    msg,
                    f.__module__,
                    f.__name__
                )

        def is_kwargs(p):
            return p.kind == inspect.Parameter.VAR_KEYWORD

        def is_keyword_compatible(p):
            return p.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY
            )

        @functools.wraps(f)
        def response_wrap(*args, **kw):
            # if controller cannot be called with extra args (utm, debug, ...),
            # call endpoint ignoring them
            params = inspect.signature(f).parameters.values()
            if not any(is_kwargs(p) for p in params):  # missing **kw
                fargs = {
                    p.name
                    for p in params
                    if is_keyword_compatible(p)
                }
                ignored = [
                    '<%s=%s>' % (k, kw.pop(k))
                    for k in list(kw)
                    if k not in fargs
                ]
                if ignored:
                    _logger.info(
                        "<function %s.%s> called ignoring args %s" % (
                            f.__module__,
                            f.__name__,
                            ', '.join(ignored)
                        )
                    )

            response = f(*args, **kw)
            # response = f(*args, **kw)
            # if isinstance(response, Response) or f.routing_type == 'json':
            #     return response

            # if isinstance(response, (bytes, str)):
            #     return Response(response)
            if isinstance(response, Response):
                return response

            # if isinstance(response, werkzeug.exceptions.HTTPException):
            #     response = response.get_response(request.httprequest.environ)
            if isinstance(response, werkzeug.wrappers.Response):
                response = Response.force_type(response)
                response.set_default()
                return response

            return response
            # _logger.warning(
            # "<function %s.%s> returns an invalid response type for an http
            # request" %
            # (f.__module__, f.__name__))
            # return response
        response_wrap.routing = routing
        response_wrap.original_func = f
        return response_wrap
    return decorator


class __patch__:
    """
    Hidden block to prevent poluting the parent scope.
    """

    def set_cookie(
        self,
        key,
        value='',
        max_age=None,
        expires=None,
        path='/',
        domain=None,
        secure=False,
        httponly=False,
        samesite=None
    ):
        # Lax is the new default for samesite, unfortunately
        # when setting samesite=None, it simply ignores the
        # value None instead of outputting the value as it is
        # set.
        # As a result werkzeug can only set it to:

        # Lax explicit
        # Strict explicit
        # Lax implicit
        if samesite is None:
            samesite = 'Lax'

        return super(Response, self).set_cookie(
            key=key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=True,
            httponly=httponly,
            samesite=samesite
        )

    Response.set_cookie = set_cookie
