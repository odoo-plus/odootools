if 'request' not in globals():
    request = None
    OrderedDict = None
    QWeb = None
    ir_http = None
    url_for = None
    re_background_image = None


def _post_processing_att(self, tagName, atts, options):
    if atts.get('data-no-post-process'):
        return atts

    atts = super(QWeb, self)._post_processing_att(tagName, atts, options)

    if tagName == 'img' and 'loading' not in atts:
        atts['loading'] = 'lazy'  # default is auto

    if (
        options.get('inherit_branding') or
        options.get('rendering_bundle') or
        options.get('edit_translations') or
        options.get('debug') or
        (request and request.session.debug)
    ):
        return atts

    website = ir_http.get_request_website()

    if website:
        website = self.env['website'].browse(website.id)

    if not website and options.get('website_id'):
        website = self.env['website'].browse(options['website_id'])

    if not website:
        return atts

    name = self.URL_ATTRS.get(tagName)
    if request and name and name in atts:
        atts[name] = url_for(atts[name])

    if not website.cdn_activated:
        return atts

    data_name = f'data-{name}'
    if name and (name in atts or data_name in atts):
        atts = OrderedDict(atts)
        if name in atts:
            atts[name] = website.get_cdn_url(atts[name])
        if data_name in atts:
            atts[data_name] = website.get_cdn_url(atts[data_name])
    if (
        isinstance(atts.get('style'), str) and
        'background-image' in atts['style']
    ):
        atts = OrderedDict(atts)
        atts['style'] = re_background_image.sub(
            lambda m: '%s%s' % (m.group(1), website.get_cdn_url(m.group(2))),
            atts['style']
        )

    return atts


QWeb._post_processing_att = _post_processing_att
