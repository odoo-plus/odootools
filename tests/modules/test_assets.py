import re

import pytest
from mock import MagicMock, patch

from odoo_tools.modules.assets import AssetsBundler


@pytest.fixture
def modules():
    odoo = MagicMock()

    models = odoo.addons.base.models

    return {
        "odoo": odoo,
        "odoo.addons": odoo.addons,
        "odoo.addons.base": odoo.addons.base,
        "odoo.addons.base.models": odoo.addons.base.models,
        "odoo.addons.base.models.assetsbundle": models.assetsbundle,
    }


class MockAsset(object):
    def __init__(self, name, data):
        self.name = name
        self.content = data

    def with_header(self, content, minimal=False):
        return f"/* {self.name} */\n{content}"

    def minify(self):
        return f"minified {self.content}"


class MockBundle(object):
    rx_css_import = r".*"

    def __init__(self, asset, file, env=None):
        self.asset = asset
        self.file = file
        self.env = env

        self.javascripts = [
            MockAsset("f1", "a"),
            MockAsset("f2", "b")
        ]

        self.stylesheets = [
            MockAsset('c1', 'c'),
            MockAsset('c2', 'd'),
            MockAsset('c2', ''),
        ]

    def preprocess_css(self):
        result = ["prep"]

        for asset in self.stylesheets:
            result.append(asset.content)
            if asset.content != '':
                asset.content = 'm'

        return "\n".join(result)


def test_assets_bundler(modules):
    asset = 'base.common'
    env = MagicMock()

    bundler = AssetsBundler(env, asset)
    assert bundler.env == env
    assert bundler.asset == asset
    assert bundler._bundle is None

    bundle_path = "odoo.addons.base.models.assetsbundle.AssetsBundle"

    with patch.dict('sys.modules', modules), \
         patch(bundle_path, MockBundle):
        assert isinstance(bundler.bundle, MockBundle)
        assert bundler._bundle is not None

        js = bundler.get_js()
        assert js == '/* f1 */\na\n/* f2 */\nb'

        js_minified = bundler.get_js(minified=True)
        assert js_minified == 'minified a;\nminified b;'

        # output with headers but output not relevant, it's
        # just mocked to confirm different outputs
        bundler = AssetsBundler(env, asset)
        css = bundler.get_css()
        assert css == (
            'prep\n\n'
            'c\n\nd\n\n\n'
            '/* /* c1 */ *//*  */\n'
            '/* m *//*  */\n'
            '/* /* c2 */ *//*  */\n'
            '/* m *//*  */'
        )

        # raw output from preprocess and matches
        bundler = AssetsBundler(env, asset)
        css_minified = bundler.get_css(minified=True)
        assert css_minified == 'prep\n\nc\n\nd\n\n\n\n\n\n'
