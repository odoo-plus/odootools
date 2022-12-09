from mock import patch, MagicMock
from odoo_tools.app.application import OdooApplication


def test_application():
    app = OdooApplication()

    assert app.env is not None
    assert app.loaded is False
    assert app.application is None
    assert app.plugins == []

    with patch.object(OdooApplication, 'execute_plugin_method') as execute:
        app.load()
        execute.assert_called()

    with patch.object(OdooApplication, 'execute_plugin_method') as execute:
        app.load()
        execute.assert_not_called()

    assert app.loaded is True


def test_application_params():
    env = MagicMock()
    plugin = MagicMock()
    plugins = [plugin]

    app = OdooApplication(env, plugins)

    plugin.register.assert_called_once_with(app)


def test_default_plugins():
    app = OdooApplication()

    assert app.plugins == []

    app.register_defaults()

    assert len(app.plugins) == 3

    assert app.loaded is False


def test_dummy_plugin():

    plugin = MagicMock()

    app = OdooApplication(plugins=[plugin])

    assert app.plugins == [plugin]

    app.load()
    app.load()

    plugin.register.assert_called_once_with(app)

    plugin.prepare_environment.assert_called_once()
    plugin.init_environment.assert_called_once()
    plugin.postinit_environment.assert_called_once()
