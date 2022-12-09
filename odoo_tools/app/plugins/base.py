import importlib
import sys
import logging

from overlaymodule import OverlayFinder

from ..utils import OdooVersionedString
from ..mixins.app import (
    DbRequestMixin,
    EnvironmentManagerMixin
)
from ..mixins.sessions import (
    FileSystemSessionStoreMixin
)


from ..mixins.http import (
    BaseApp,
    BaseWSGIApp,
    StaticAssetsMiddleware,
    AddonsLoaderMiddleware,
)

_logger = logging.getLogger(__name__)


class Plugin(object):
    def __init__(self, *args, **kwargs):
        self.app = None

    def register(self, application):
        self.app = application

    def init_environment(self):
        pass

    def postinit_environment(self):
        pass

    def prepare_environment(self):
        pass


class OverlayModulePlugin(Plugin):
    def __init__(self, odoo_path=None, overlays=None, include_default=True):
        if odoo_path is None:
            spec = importlib.util.find_spec('odoo')
            if spec is not None:
                odoo_path = spec.submodule_search_locations[0]

        if overlays is None:
            overlays = []

        default_overlays = []

        if include_default:
            default_overlays += self.default_overlays()

        self.odoo_path = odoo_path
        self.overlays = default_overlays + overlays

    def default_overlays(self):
        return [
            "odoo_tools.overlays.common",
            OdooVersionedString("odoo_tools.overlays.v{version_info[0]}"),
        ]

    def prepare_environment(self):
        if self.odoo_path is None:
            _logger.info(
                "Cannot define the overlay without knowing where "
                "odoo is located"
            )
            return

        finder = OverlayFinder(
            'odoo',
            self.odoo_path,
            self.overlays,
        )

        sys.meta_path.insert(
            0, finder
        )


class AddonsPathPlugin(Plugin):
    def __init__(self, paths):
        self.paths = paths

    def init_environment(self):
        from odoo import addons

        odoo_path = self.app.env.path().parent
        odoo_addons_path = odoo_path / 'addons'

        paths = self.paths + list(self.app.env.addons_paths())

        if odoo_addons_path.exists():
            paths.append(odoo_addons_path)

        for path in paths[::-1]:
            if str(path) not in addons.__path__:
                addons.__path__.insert(0, str(path))


class InitOdooPlugin(Plugin):
    def __init__(self, db_name=None):
        self.db_name = db_name

    def init_environment(self):
        self.load_configuration()

    def postinit_environment(self):
        self.preload_databases()

    def load_configuration(self):
        self.app.env.manage.initialize_odoo()

    def get_db_filter(self):
        odoo_version = f"{self.app.env.odoo_version()}.0"

        version_filter = {
            "db_name": self.db_name,
            "filter_version": odoo_version
        }

        return version_filter

    def get_databases(self):
        version_filter = self.get_db_filter()

        manage = self.app.env.manage
        for db in manage.db_list(**version_filter):
            yield db

    def preload_databases(self):
        from odoo.modules.registry import Registry

        # odoo_version = f"{self.app.env.odoo_version()}.0"
        for db in self.get_databases():
            try:
                # TODO maybe load the registry with Registry(db) instead.
                Registry.new(db["name"])
            except Exception:
                _logger.error(
                    f"Couldn't load database registry {db['name']}",
                    exc_info=True
                )


class SessionStorePlugin(Plugin):
    def __init__(self, session_type=None):
        if session_type is None:
            session_type = FileSystemSessionStoreMixin
        self.session_type = session_type

    def prepare_environment(self):
        self.app.application_mixins.insert(0, self.session_type)


class DbRoutePlugin(Plugin):
    def prepare_environment(self):
        self.app.application_mixins.insert(0, DbRequestMixin)


# TODO Remove
#   class BaseOdooApp(Plugin):
#       def prepare_environment(self):
#           from odoo.http import Root
#           self.app.application_mixins.insert(0, Root)


class AssetsPlugin(Plugin):
    def __init__(self, asset_middleware):
        self.asset_middleware = asset_middleware

    def prepare_environment(self):
        self.app.application_mixins.insert(0, self.asset_middleware)


class OdooWSGIHandler(Plugin):
    def __init__(self):
        self.app_type = None

    def register(self, app):
        super().register(app)

        app.application_mixins = [
            EnvironmentManagerMixin,
            AddonsLoaderMiddleware,
            BaseWSGIApp,
            BaseApp,
            object
        ]

    def get_app_type(self):
        if self.app_type is None:
            self.app_type = type(
                'Root',
                tuple(self.app.application_mixins),
                {}
            )

        return self.app_type

    def init_environment(self):
        self.app.application_type = self.get_app_type()
        self.app.application = self.app.application_type(self)

        from odoo import http

        # Todo maybe patch the class of the live object instead
        # of replacing it
        http.Root = self.app.application_type
        http.root = self.app.application
