# import sys
import psycopg2
from contextlib import closing, contextmanager
import logging
from itertools import groupby

from .objects import CompanySpec
from ..entrypoints import execute_entrypoint, entrypoint
from ..exceptions import InstallModulesError

_logger = logging.getLogger(__name__)


# When parsing an odoo config multiple times,
# it will complain that some keys aren't defined.
# Some of those keys are from config that can't be saved
# back to the configuration file.
resettable_keys = [
    "load_language",
]


@contextmanager
def manage(env, manager=None):
    if manager and env.odoo_version() < 15:
        with manager.manage():
            yield
    else:
        yield


def set_missing_keys(config, key, value):
    try:
        # odoo.tools.configmanager doesn't handle "in"
        if key not in config:
            config[key] = value
    except KeyError:
        config[key] = value


def before_config(man):
    man.config.config_file = man.environment.context.odoo_rc

    for key in resettable_keys:
        set_missing_keys(man.config, key, False)


def after_config(man):
    # Import models first to prevent
    # cannot import name 'Model' from partially initialized module
    # 'odoo.models'
    # (most likely due to a circular import)
    # import odoo # noqa
    # from odoo import models # noqa 
    # from odoo.osv import expression # noqa
    from odoo.service.server import load_server_wide_modules

    if hasattr(man, 'without_demo') and man.without_demo:
        man.config['without_demo'] = True
        for key in man.config['demo'].keys():
            man.config['demo'][key] = False

    if hasattr(man, 'languages') and man.languages:
        man.config['load_language'] = man.languages

    load_server_wide_modules()


def initialize_odoo(man):
    _logger.info("Init Odoo")
    import odoo
    from odoo.release import version_info

    man.config._parse_config([])

    man.environment.sync_options()

    if man.environment.context.init_logger:
        odoo.netsvc.init_logger()

    if version_info[0] >= 14:
        man.config._warn_deprecated_options()

    odoo.modules.module.initialize_sys_path()


def ensure_db(man):
    _logger.info("Ensure db exists")
    import odoo
    from odoo.service.db import _create_empty_database
    try:
        _create_empty_database(man.database)
    except odoo.service.db.DatabaseExists:
        pass


def setup_company(man):
    country = man.company_spec.country_code

    with man.env() as env:
        # Post Init database with base module
        Country = env['res.country']
        company_country = Country.search(
            [
                ['code', 'ilike', country]
            ],
            limit=1
        )
        env.company.country_id = company_country.id


class DbApi(object):

    def __init__(self, manage, database):
        self.environment = manage.environment
        self.database = database
        self.config = manage.config
        self._entrypoint_loaded = False
        self.without_demo = True

    def mark_modules(self, modules, force=False):
        to_install = {mod for mod in modules}
        to_update = set()

        if not force:
            try:
                with self.env() as env:
                    IrModule = env['ir.module.module']
                    installed_modules = IrModule.search(
                        [
                            ['name', 'in', list(to_install)],
                            ['state', '=', 'installed'],
                        ],
                    )
                    for mod in installed_modules:
                        to_install.remove(mod.name)
                        to_update.add(mod.name)
            except psycopg2.OperationalError:
                _logger.error(
                    "SQL Error",
                    exc_info=True
                )
                return
            except KeyError:
                _logger.error(
                    "Odoo doesn't seem to be initialized",
                    exc_info=True
                )
                return
            except Exception:
                _logger.error(
                    "Something went wrong while searching installed modules",
                    exc_info=True
                )
                return

        for mod in to_install:
            self.config['init'][mod] = 1

        for mod in to_update:
            self.config['update'][mod] = 1

    def unmark_modules(self):
        for key in self.config['init'].keys():
            self.config['init'][key] = False

        for key in self.config['update'].keys():
            self.config['update'][key] = False

    def init(self, modules, country, language="en_US", without_demo=True):
        company = CompanySpec(country_code=country)

        self.company_spec = self.environment.manage.company_spec = company
        self.without_demo = self.environment.manage.without_demo = without_demo
        self.languages = self.environment.manage.languages = language

        self.environment.manage.initialize_odoo()

        self.install_modules_registry(
            ["base"],
            phase="Initializing database",
            event="initdb",
            force=True
        )

        to_install = modules.copy()
        if 'base' in to_install:
            to_install.remove('base')

        self.install_modules_registry(
            modules,
            phase="Installing other modules",
            event="install_modules"
        )

    def default_entrypoints(self):
        if self._entrypoint_loaded:
            return

        self._entrypoint_loaded = True

        entrypoint("odoo_tools.manage.before_config")(before_config)
        entrypoint("odoo_tools.manage.after_config")(after_config)

        entrypoint("odoo_tools.manage.initialize_odoo")(initialize_odoo)
        entrypoint("odoo_tools.manage.before_initdb")(ensure_db)
        entrypoint("odoo_tools.manage.after_initdb")(setup_company)

    def install_modules(
        self,
        modules,
        force=False,
        phase="unknown",
        event="install_modules"
    ):
        self.environment.manage.initialize_odoo()
        self.install_modules_registry(
            modules,
            phase=phase,
            event=event
        )

    def install_modules_registry(
        self,
        modules,
        phase="unknown",
        force=False,
        event=None
    ):
        from odoo.service.server import preload_registries

        if event:
            execute_entrypoint(
                "odoo_tools.manage.before_{}".format(event),
                self
            )

        self.mark_modules(modules, force=force)

        # Creates a registry to be called to install
        rc = preload_registries([self.database])
        if rc != 0:
            _logger.error(
                "Failed installing or updating modules in phase %s",
                phase
            )
            raise InstallModulesError("Failed to install {}".format(modules))

        # Disable init for all modules
        self.unmark_modules()
        if event:
            execute_entrypoint(
                "odoo_tools.manage.after_{}".format(event),
                self
            )

    def uninstall_modules(
        self,
        modules
    ):
        self.environment.manage.initialize_odoo()

        with self.env() as env:
            IrModule = env['ir.module.module']

            installed_modules = IrModule.search(
                [
                    ['name', 'in', list(modules)],
                    ['state', '!=', 'uninstalled'],
                ],
            )

            installed_modules.button_immediate_uninstall()

    def export_translation_terms(self, languages, modules):
        """
        Export terms grouped by module
        """
        # TODO create a unified term exporter. The one from Odoo14 is
        # much better than previous versions. It could be a good start
        # as resources don't need to have odoo access.
        # Then implement a loader that can extract terms from fields
        # like Selection and translatable fields.
        #
        # Odoo14 implement selections through ir.models.fields.selection
        # while previous versions use the field.selection attribute.
        #
        # We don't really have to complicate ourselves as in odoo14
        # It's just a basic model being exported (need to guess proper xmlid)
        # While on earlier versions of odoo we can simply use a custom loader
        # for selection field.
        # In practice we could attempt to export translations using both format
        # and odoo should simply ignore older formats and everyone is happy.
        try:
            # Odoo 10, 11, 12, 13
            from odoo.tools import trans_generate
        except ImportError:
            # Odoo 14
            from odoo.tools.translate import TranslationModuleReader

            def trans_generate(language, modules, cr):

                reader = TranslationModuleReader(
                    cr,
                    modules=modules,
                    lang=language
                )
                return [
                    x
                    for x in reader
                ]

        def get_key(key_id):
            def wrap(value):
                return value[key_id]
            return wrap

        with self.env() as env:
            for language in languages:
                translations = trans_generate(
                    language,
                    modules,
                    env.cr
                )

                translations.sort()

                for module, terms in groupby(translations, key=get_key(0)):
                    yield language, module, terms

        _logger.info('translation file written successfully')

    @contextmanager
    def env(self, uid=None, ctx=None):
        import odoo
        from odoo.api import Environment
        from psycopg2 import errors

        if uid is None:
            uid = 1

        if ctx is None:
            ctx = {}

        odoo_registry = odoo.registry(self.database)

        # Post Init database with base module
        with manage(self.environment, manager=Environment):
            with closing(odoo_registry.cursor()) as cr:
                try:
                    env = Environment(cr, uid, ctx)
                    yield env
                except errors.InFailedSqlTransaction:
                    env.cr.rollback()

                try:
                    env.cr.commit()
                except Exception:
                    env.cr.rollback()
