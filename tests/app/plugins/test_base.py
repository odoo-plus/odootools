from pathlib import Path
import pytest
from mock import MagicMock, patch
import sys
from odoo_tools.app.application import OdooApplication
from odoo_tools.app.plugins.base import (
    Plugin,
    OverlayModulePlugin,
    AddonsPathPlugin,
    InitOdooPlugin,
    SessionStorePlugin,
    DbRoutePlugin,
    AssetsPlugin,
    OdooWSGIHandler,
)


@pytest.fixture
def modules():
    odoo = MagicMock()

    return {
        'odoo': odoo,
        'odoo.http': odoo.http,
        'odoo.addons': odoo.addons,
        'odoo.modules': MagicMock(),
        'odoo.modules.registry': MagicMock(),
        'odoo.modules.module': MagicMock(),
    }


class MockException(Exception):
    pass


def test_base_plugin():
    app = OdooApplication()
    plugin = Plugin()

    assert plugin.app is None
    plugin.register(app)
    assert plugin.app == app

    app.add_plugin(plugin)
    app.load()

    assert app.loaded is True


def test_overlay_plugin():
    odoo_spec = MagicMock()
    odoo_spec.submodule_search_locations = ['/test/odoo']
    meta_mock = sys.meta_path[:]

    with patch('importlib.util.find_spec') as find_spec, \
         patch('odoo_tools.app.plugins.base.OverlayFinder') as Ovf, \
         patch('sys.meta_path', meta_mock):
        find_spec.return_value = odoo_spec
        odoo_path = MagicMock()
        plugin = OverlayModulePlugin(odoo_path)
        assert plugin.odoo_path == odoo_path

        plugin = OverlayModulePlugin()
        assert plugin.odoo_path == '/test/odoo'

        plugin = OverlayModulePlugin(overlays=['test.odoo.common'])
        overlays = plugin.default_overlays() + ['test.odoo.common']
        assert plugin.overlays == overlays

        default_overlays = plugin.default_overlays()
        overlay_tpl = 'odoo_tools.overlays.v{version_info[0]}'
        assert default_overlays[0] == 'odoo_tools.overlays.common'
        assert default_overlays[1].template == overlay_tpl
        assert len(default_overlays) == 2

        plugin.odoo_path = None
        plugin.prepare_environment()
        assert not isinstance(sys.meta_path[0], MagicMock)

        plugin.odoo_path = '/test/odoo'
        plugin.prepare_environment()

        assert sys.meta_path[0]._mock_new_parent == Ovf
        Ovf.assert_called_once()


def test_addons_path_plugin(modules):
    app = MagicMock()

    app.env.path.return_value = Path('/test/odoo/odoo')
    app.env.addons_paths.return_value = []

    paths = ['/test2/odoo/addons', '/test2/odoo/addons2']
    plugin = AddonsPathPlugin(paths)
    assert plugin.paths == paths

    odoo = modules['odoo']
    odoo.addons.__path__ = []

    with patch.dict('sys.modules', modules):
        plugin.register(app)
        plugin.init_environment()
        assert odoo.addons.__path__ == paths

    # Check that adding the odoo addons works if they're in
    # /repo/addons when odoo is in /repo/odoo
    with patch.dict('sys.modules', modules), \
         patch.object(Path, 'exists') as exists:
        exists.return_value = True
        plugin.register(app)
        plugin.init_environment()
        assert odoo.addons.__path__ == ['/test/odoo/addons'] + paths


def test_init_odoo_plugin(modules):
    app = MagicMock()

    db = 'test'

    plugin = InitOdooPlugin(db)

    plugin.register(app)

    plugin.prepare_environment()
    plugin.init_environment()

    app.env.manage.initialize_odoo.assert_called_once()
    app.env.manage.db_list.return_value = [{'name': 'test'}]
    app.env.odoo_version.return_value = 15

    assert app.env.odoo_version == plugin.app.env.odoo_version
    assert plugin.get_db_filter() == {
        "db_name": "test",
        "filter_version": "15.0",
    }

    with patch.dict('sys.modules', modules):
        plugin.postinit_environment()

    registry = modules['odoo.modules.registry']
    registry.Registry.new.side_effect = MockException

    # Does not crash if db can't be loaded
    with patch.dict('sys.modules', modules):
        plugin.postinit_environment()


def test_session_store_plugin():
    app = MagicMock()
    app.application_mixins = [1]
    store = MagicMock()

    plugin = SessionStorePlugin(store)
    plugin.register(app)
    assert app.application_mixins == [1]

    plugin.prepare_environment()
    assert app.application_mixins == [store, 1]

    app.application_mixins = [1]
    plugin = SessionStorePlugin()
    plugin.register(app)
    plugin.prepare_environment()
    assert app.application_mixins != []
    assert app.application_mixins[-1] == 1
    assert len(app.application_mixins) == 2


def test_db_route():
    app = MagicMock()
    app.application_mixins = [1]

    plugin = DbRoutePlugin()
    plugin.register(app)
    plugin.prepare_environment()

    assert app.application_mixins[-1] == 1
    assert len(app.application_mixins) == 2


def test_assets_plugin():
    app = MagicMock()
    app.application_mixins = [1]

    mixin = MagicMock()
    
    plugin = AssetsPlugin(mixin)
    plugin.register(app)
    plugin.prepare_environment()
    assert app.application_mixins == [mixin, 1]


def test_wsgi_handler(modules):
    app = MagicMock()
    app.application_mixins = []

    plugin = OdooWSGIHandler()
    assert app.application_mixins == []

    plugin.register(app)
    assert app.application_mixins != []
    assert app.application_mixins[-1] == object

    odoo = modules['odoo']
    odoo.addons.__path__ = []

    with patch.dict('sys.modules', modules):
        plugin.init_environment()

        assert odoo.http.Root == plugin.get_app_type()
        assert isinstance(odoo.http.root, plugin.get_app_type())
