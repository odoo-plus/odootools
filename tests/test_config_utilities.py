import sys
from pathlib import Path
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
from odoo_tools.configuration.pip import pip_command
from odoo_tools.configuration.misc import find_in_path
from odoo_tools.utilities.loaders import FileLoader
from odoo_tools.exceptions import FileParserMissingError
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


def test_pip_command():
    executable = sys.executable
    base_args = [executable, '-m', 'pip', 'install']

    empty = pip_command()

    assert empty == base_args

    user_args = pip_command(user=True)
    assert user_args == base_args + ['--user']

    upgrade_args = pip_command(upgrade=True)
    assert upgrade_args == base_args + ['-U']

    target = Path("/tmp/fun")
    target_args = pip_command(target=target)
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert target_args == base_args + [
        '--target', str(target),
        '--implementation', 'cp',
        '--python', python_version,
        '--no-deps'
    ]

    combined_args = pip_command(user=True, upgrade=True)
    assert combined_args == base_args + ['--user', '-U']


def test_file_loader(tmp_path):
    loader = FileLoader()

    raw_file = tmp_path / 'raw_file'
    with raw_file.open('w') as fout:
        fout.write("hey")

    loaders = loader.get_loaders(raw_file)
    assert loaders == []

    data = loader.load_file(raw_file)
    assert data == "hey"

    raw_txt = tmp_path / 'raw.txt'
    with raw_txt.open('w') as fout:
        fout.write("hey")

    with pytest.raises(FileParserMissingError):
        loader.load_file(raw_txt)

    loader.parsers['.txt'] = lambda data: data

    data = loader.load_file(raw_txt)
    assert data == "hey"


def test_find_in_path(tmp_path):
    path = find_in_path("/usr/bin/python")
    assert path == "/usr/bin/python"

    path = find_in_path("../fun")
    assert path == "../fun"

    python_exec = Path(sys.executable)
    python_binary = python_exec.name
    binary_path = python_exec.parent

    path = find_in_path(python_binary, paths=[binary_path])
    assert path == str(python_exec)
