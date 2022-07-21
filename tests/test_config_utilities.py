import pytest
from unittest.mock import patch, MagicMock
from odoo_tools.utilities.config import (
    parse_value,
    get_odoo_casts,
    get_env_params,
    custom_env_params
)
from odoo_tools.utils import ConfigParser
from odoo_tools.api.environment import Environment
from configparser import NoOptionError


def mock_option(param, my_default):
    opt = MagicMock()
    opt.my_default = my_default
    opt.get_opt_string.return_value = param
    return opt


def test_parse_config():
    val = parse_value('True')
    assert val is True

    val = parse_value(True)
    assert val is True

    val = parse_value(False)
    assert val is False

    val = parse_value('False')
    assert val is False

    val = parse_value('None')
    assert val is None

    val = parse_value(None)
    assert val is None


def test_odoo_casts():
    with patch.object(Environment, 'odoo_config') as method:
        config = MagicMock()
        config.casts = {
            'limit_request': mock_option(
                '--limit_request', 8192
            ),
            'init': mock_option(
                '--init', None
            ),
            'server_wide_modules': mock_option(
                '--load', 'base,web'
            )
        }
        method.return_value = config

        env = Environment()
        res = get_odoo_casts(env)

        parsed_value = {
            'ODOO_INIT': ('init', None),
            'ODOO_LIMIT_REQUEST': ('limit_request', 8192),
            'ODOO_LOAD': ('server_wide_modules', 'base,web')
        }

        assert res == parsed_value

        res = get_env_params(env, 9000)

        parsed_value2 = {
            'ODOO_INIT': ('init', None),
            'ODOO_LIMIT_REQUEST': ('limit_request', 8192),
            'ODOO_LOAD': ('server_wide_modules', 'base,web')
        }

        parsed_value2.update(custom_env_params)

        assert res == parsed_value2


def test_config_set_defaults():
    config = ConfigParser()

    config.set_defaults({'name': 'ok'})

    val = config.get('options', 'name')

    assert val == 'ok'

    config.set('options', 'name', 'ok')

    config.set_defaults({})

    with pytest.raises(NoOptionError):
        config.get('options', 'name')
