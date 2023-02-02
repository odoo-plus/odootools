import os
from pathlib import Path
from mock import patch
from odoo_tools.api.context import Context
from odoo_tools.configuration.misc import cd
from odoo_tools.env import EnvironmentVariables, EnvironmentVariable, StoredEnv


def test_empty_context():
    context = Context()

    assert context.custom_paths == set()
    assert context.excluded_paths == set()
    assert context.extra_apt_packages == set()


def test_empty_context_odoorc(tmp_path):
    odoorc = tmp_path / 'odoo.cfg'

    with cd(tmp_path):
        context = Context()
        assert context.odoo_rc == odoorc


def test_context_envvars(tmp_path):

    excluded_paths = [
        tmp_path/'excluded1',
        tmp_path/'excluded2'
    ]

    extra_paths = [
        tmp_path / 'extra1',
        tmp_path / 'extra2'
    ]

    vals = dict(
        ODOO_EXTRA_PATHS=",".join([str(path) for path in extra_paths]),
        ODOO_STRICT_MODE="TRUE",
        ODOO_REQUIREMENTS_FILE=str(tmp_path/'requirements.txt'),
        ODOO_EXCLUDED_PATHS=",".join([str(path) for path in excluded_paths]),
        ODOO_DISABLED_MODULES="disabled1,disabled2",
        ODOO_RC=str(tmp_path / 'ODOORC')
    )

    with patch.dict(os.environ, vals):
        context = Context.from_env()

        assert context.custom_paths == set(extra_paths)
        assert context.odoo_rc == tmp_path / 'ODOORC'
        assert context.excluded_paths == set(excluded_paths)
        assert context.disabled_modules == {'disabled1', 'disabled2'}
        assert context.strict_mode is True


def test_environment_variables():
    vals = {}

    with patch.dict(os.environ, vals, clear=True):
        env = EnvironmentVariables()
        assert env._values == {}
        assert env.ODOO_RC is None
        assert env._values == {'ODOO_RC': None}
        env.ODOO_RC = '/tmp'
        assert env._values == {'ODOO_RC': '/tmp'}
        assert os.environ['ODOO_RC'] == '/tmp'

        values = env.values()
        assert 'ODOO_RC' in values and values['ODOO_RC'] == '/tmp'
        assert 'ODOO_EXTRA_APT_PACKAGES' in values
        assert values['ODOO_EXTRA_APT_PACKAGES'] == set()
        assert env.ODOO_EXTRA_APT_PACKAGES == set()


def test_env_properties():
    vals = {
        'val2': '1',
        'val3': '2',
        'val5': ''
    }

    with patch.dict(os.environ, vals):

        class MyObj(object):
            __fields__ = set()

            val1 = EnvironmentVariable(alternate_names=['val2', 'val4'])
            val3 = StoredEnv()
            val5 = StoredEnv(readonly=True)

            def __init__(self):
                self._values = {}

        obj = MyObj()

        assert obj.val1 == '1'
        assert obj.val3 == '2'

        os.environ['val1'] = '4'
        os.environ['val2'] = '5'
        os.environ['val4'] = '6'
        os.environ['val3'] = '3'

        # Stored doesn't refetch value from env
        assert obj.val3 == '2'
        # Unstored always check env
        assert obj.val1 == '4'

        # Check alternate names
        del os.environ['val1']
        assert obj.val1 == '5'

        del os.environ['val2']
        assert obj.val1 == '6'

        obj.val3 = "fun"
        assert os.environ['val3'] == "fun"

        obj.val5 = "whoa"
        assert obj.val5 == ''
        assert os.environ['val5'] == ''
        assert obj._values['val5'] == ''
