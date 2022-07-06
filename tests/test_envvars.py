import os
from mock import patch
from odoo_tools.api.context import Context
from odoo_tools.configuration.misc import cd


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
