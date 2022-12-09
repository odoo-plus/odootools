if 'request' not in globals():
    request = None
    IrHttp = None
    werkzeug = None


@classmethod
def _match(cls, *args, **kwargs):
    routing_error = None
    func = None

    try:
        rule, arguments = super(IrHttp, cls)._match(*args, **kwargs)
        func = rule.endpoint
        request.is_frontend = func.routing.get('website', False)
    except werkzeug.exceptions.NotFound as exc:
        path_components = request.httprequest.path.split('/')
        request.is_frontend = (
            len(path_components) < 3 or
            path_components[2] != 'static' or
            '.' not in path_components[-1]
        )
        routing_error = exc

    request.is_frontend_multilang = (
        not func or
        (
            func and
            request.is_frontend and
            func.routing.get('multilang', func.routing['type'] == 'http')
        )
    )
    request.routing_iteration = getattr(request, 'routing_iteration', 0) + 1

    cls._geoip_setup_resolver()
    cls._geoip_resolve()

    if request.is_frontend:
        cls._apply_frontend(func)

    if routing_error:
        raise routing_error

    return rule, arguments


@classmethod
def _apply_frontend(cls, func):
    cls._add_dispatch_parameters(func)

    path = request.httprequest.path.split('/')
    default_lg_id = cls._get_default_lang()
    if request.routing_iteration == 1:
        is_a_bot = cls.is_a_bot()
        nearest_lang = (
            not func and
            cls.get_nearest_lang(
                request.env['res.lang']._lang_get_code(path[1])
            )
        )
        url_lg = nearest_lang and path[1]

        # The default lang should never be in the URL, and a wrong lang
        # should never be in the URL.
        wrong_url_lg = (
            url_lg and (
                url_lg != request.lang.url_code or
                url_lg == default_lg_id.url_code
            )
        )
        # The lang is missing from the URL if multi lang is enabled for
        # the route and the current lang is not the default lang.
        # POST requests are excluded from this condition.
        missing_url_lg = (
            not url_lg and
            request.is_frontend_multilang and
            request.lang != default_lg_id and
            request.httprequest.method != 'POST'
        )
        # Bots should never be redirected when the lang is missing
        # because it is the only way for them to index the default lang.
        if wrong_url_lg or (missing_url_lg and not is_a_bot):
            if url_lg:
                path.pop(1)
            if request.lang != default_lg_id:
                path.insert(1, request.lang.url_code)
            path = '/'.join(path) or '/'
            # routing_error = None
            redirect = request.redirect(
                path + '?' + request.httprequest.query_string.decode('utf-8')
            )
            redirect.set_cookie('frontend_lang', request.lang.code)
            return redirect
        elif url_lg:
            request.uid = None
            if request.httprequest.path == '/%s/' % url_lg:
                # special case for homepage controller, mimick
                # `_postprocess_args()` redirect
                path = request.httprequest.path[:-1]
                if request.httprequest.query_string:
                    path += (
                        '?' + request.httprequest.query_string.decode('utf-8')
                    )
                return request.redirect(path, code=301)
            path.pop(1)
            # routing_error = None
            return cls.reroute('/'.join(path) or '/')
        elif missing_url_lg and is_a_bot:
            # Ensure that if the URL without lang is not redirected, the
            # current lang is indeed the default lang, because it is the
            # lang that bots should index in that case.
            request.lang = default_lg_id
            request.context = dict(request.context, lang=default_lg_id.code)

    if request.lang == default_lg_id:
        context = dict(request.context)
        context['edit_translations'] = False
        request.context = context


IrHttp._match = _match
IrHttp._apply_frontend = _apply_frontend
