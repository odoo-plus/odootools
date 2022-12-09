if 'request' not in globals():
    request = None
    SUPERUSER_ID = None
    registry = None
    api = None
    Http = None


@classmethod
def _match(cls, path_info, key=None):
    if request.session.db:
        reg = registry(request.session.db)
        with reg.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            request.website_routing = env['website'].get_current_website().id

    key = key or (request and request.website_routing)
    return super(Http, cls)._match(path_info, key=key)


Http._match = _match
