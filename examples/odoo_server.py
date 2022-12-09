from pathlib import Path
from odoo_tools.app.plugins import (
    InitOdooPlugin,
    AddonsPathPlugin,
    OverlayModulePlugin,
    LoggingPlugin,
    OdooWSGIHandler,
    SessionStorePlugin,
    DbRoutePlugin,
    AssetsPlugin,
)
from odoo_tools.app.mixins.http import StaticAssetsMiddleware
from odoo_tools.app.mixins.sessions import FileSystemSessionStoreMixin
from odoo_tools.app import OdooApplication
from odoo_tools.app.utils import OdooVersionedString


base_path_odoo = Path.cwd() / 'odoo'

app = OdooApplication()

# OdooTools overlays
overlays = [
    "odoo_tools.overlays.common",
    OdooVersionedString("odoo_tools.overlays.v{version_info[0]}"),
]

# Main plugin that allow extending odoo itself. This plugin
# is more or less necessary
app.add_plugin(
    OverlayModulePlugin(str(base_path_odoo / 'odoo'), overlays)
)

# Define plugin to load the addons_path
app.add_plugin(AddonsPathPlugin([
    str(base_path_odoo / 'addons'),
    str(base_path_odoo / 'odoo/addons'),
]))

# app.add_plugin(InitOdooPlugin('test_aws'))
app.add_plugin(OdooWSGIHandler())

# Dispatch static assets
app.add_plugin(AssetsPlugin(StaticAssetsMiddleware))

# Define a SessionStore
app.add_plugin(SessionStorePlugin(FileSystemSessionStoreMixin))

# Define a DbRoute dispatcher will determine
# routes that require a db
app.add_plugin(DbRoutePlugin())

# Define the logger (default StreamLogger)
app.add_plugin(LoggingPlugin())

app.load()

handler = app.application
