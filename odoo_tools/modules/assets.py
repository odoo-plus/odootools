import re


class AssetsBundler(object):
    def __init__(self, env, asset):
        self.env = env
        self.asset = asset
        self._bundle = None

    @property
    def bundle(self):
        if not self._bundle:
            self._bundle = self.get_bundle()

        return self._bundle

    def get_bundle(self):
        from odoo.addons.base.models.assetsbundle import AssetsBundle
        self.files = self.get_files()
        return AssetsBundle(self.asset, self.files[0], env=self.env)

    def get_files(self):
        qweb = self.env['ir.qweb']
        files = qweb._get_asset_content(self.asset)
        return files

    def get_js(self, minified=False):
        result = []

        if minified:
            for js in self.bundle.javascripts:
                result.append(f"{js.minify()};")
        else:
            for js in self.bundle.javascripts:
                result.append(js.with_header(js.content, minimal=False))

        return "\n".join(result)

    def get_css(self, minified=False):
        from odoo.addons.base.models.assetsbundle import AssetsBundle

        data = self.bundle.preprocess_css()

        matches = []
        data = re.sub(
            AssetsBundle.rx_css_import,
            lambda matchobj: matches.append(matchobj.group(0)) and '',
            data
        )

        if minified:
            matches.append(data)
        else:
            for style in self.bundle.stylesheets:
                if not style.content:
                    continue

                content = style.with_header(style.content)

                content = re.sub(
                    AssetsBundle.rx_css_import,
                    lambda matchobj: f"/* {matchobj.group(0)} */",
                    content
                )

                matches.append(content)

        return "\n".join(matches)
