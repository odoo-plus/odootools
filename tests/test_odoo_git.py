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

    with patch.dict(os.environ, vals, clear=True):
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
