import os
import sys
import pytest
from collections import defaultdict
from mock import patch, MagicMock
from odoo_tools.api.objects import Manifest

from odoo_tools.entrypoints import entrypoint
from odoo_tools import entrypoints
from odoo_tools.docker.user_entrypoint import (
    setup_env_config
)


@pytest.mark.skipif(
    'TEST_ODOO' not in os.environ,
    reason="Testing Odoo is disabled"
)
def test_check_odoo(odoo_env):
    odoo_env.check_odoo()


@pytest.mark.skipif(
    'TEST_ODOO' not in os.environ,
    reason="Testing Odoo is disabled"
)
def test_get_odoo_addons(odoo_env):
    assert len(odoo_env.addons_paths()) == 1

    bus_module = odoo_env.modules.get('bus')

    assert bus_module.technical_name == 'bus'

    from odoo.tools import config

    assert config == odoo_env.odoo_config()


@pytest.mark.skipif(
    'TEST_ODOO' not in os.environ,
    reason="Testing Odoo is disabled"
)
def test_env_options(odoo_env):
    from odoo.tools import config

    config['workers'] = 0

    vals = dict(
        ODOO_LOAD="web,base,fun",
        ODOO_WORKERS="3",
        ODOO_DATABASE="fun"
    )

    with patch.dict(os.environ, vals):
        conf = odoo_env.env_options()

        with odoo_env.config() as conf1:
            conf1.set('queue', 'channel', 1)

        assert conf['workers'] == "3"
        assert conf['server_wide_modules'] == "web,base,fun"
        assert conf['db_name'] == 'fun'

        assert config.get('server_wide_modules') == 'base,web'
        assert config.get('db_name') is False
        assert config.get('workers') == 0
        assert config.misc.get('queue') is None

        odoo_env.sync_options()

        assert config.get('server_wide_modules') == 'web,base,fun'
        assert config.get('db_name') == "fun"
        assert config.get('workers') == "3"
        assert config.misc['queue']['channel'] == '1'


@pytest.mark.skipif(
    'TEST_ODOO' not in os.environ,
    reason="Testing Odoo is disabled"
)
def test_release(odoo_release):
    from odoo.tools import config

    assert config == odoo_release.manage.config

    call_stack = []

    @entrypoint("odoo_tools.manage.before_config")
    def before_config(manage):
        call_stack.append('before_config')

    @entrypoint("odoo_tools.manage.initialize_odoo")
    def initialize_odoo(manage):
        call_stack.append("initialize_odoo")

    @entrypoint("odoo_tools.manage.after_config")
    def after_config(manage):
        call_stack.append("after_config")

    odoo_release.manage.initialize_odoo()

    assert call_stack == ["before_config", "initialize_odoo", "after_config"]


@pytest.mark.skipif(
    'TEST_ODOO' not in os.environ,
    reason="Testing Odoo is disabled"
)
def test_init_db(odoo_release):
    entrypoints.custom_entrypoints = defaultdict(list)
    dbname = "test_{}_{}_{}".format(
        os.environ['TEST_ODOO'],
        sys.version_info.major,
        sys.version_info.minor,
    )
    db = odoo_release.manage.db(dbname)

    def initialize_odoo_test(manage):
        assert 1 == 1

    def setup_company_test(db):
        with db.env() as env:
            assert 'res.country' in env
            ResCountry = env['res.country']
            assert len(ResCountry.search([])) > 0

    entrypoint("odoo_tools.manage.initialize_odoo")(initialize_odoo_test)
    entrypoint("odoo_tools.manage.after_initdb")(setup_company_test)

    db.default_entrypoints()

    assert odoo_release.path().name == 'odoo'
    assert len(odoo_release.addons_paths()) == 1
    assert odoo_release.modules.get('base') is not None

    db.init(
        modules=["sale", "stock"],
        country="CA",
        language="fr_CA",
        without_demo=False
    )

    db.install_modules(["website"])

    db.uninstall_modules(["website", "stock"])

    with db.env() as env:
        IrModule = env['ir.module.module']
        modules = IrModule.search([['name', 'in', ['website', 'stock']]])
        for mod in modules:
            assert mod.state == 'uninstalled'

    website = odoo_release.modules.get('sale')

    website.export_translations(db, ['fr_CA'])


@pytest.mark.skipif(
    'TEST_ODOO' not in os.environ,
    reason="Requires odoo to fetch env_options"
)
def test_set_env_config(odoo_env, tmp_path):
    new_environ = {}

    with patch.dict(os.environ, new_environ, clear=True):
        setup_env_config(odoo_env)

    with odoo_env.config():
        assert odoo_env.get_config('db_host') is False

    new_environ = {
        "ODOO_DATABASE": "db1",
        "ODOO_LOAD": "web,base,kankan",
        "ODOO_WITHOUT_DEMO": "web",
    }

    with patch.dict(os.environ, new_environ, clear=True):
        setup_env_config(odoo_env)

    with odoo_env.config():
        assert odoo_env.get_config('db_name') == 'db1'
        assert odoo_env.get_config('server_wide_modules') == 'web,base,kankan'
        assert odoo_env.get_config('without_demo') == 'web'


@pytest.mark.skipif(
    'TEST_ODOO' not in os.environ,
    reason="Requires odoo to fetch env_options"
)
def test_export_translations(tmp_path):
    db = MagicMock()

    db.export_translation_terms.return_value = [
        ('fr', 'mod', []),
    ]

    manifest = Manifest(
        path=tmp_path / 'mod'
    )

    po_files = manifest.export_translations(
        db, ['fr']
    )

    assert len(po_files) == 1
