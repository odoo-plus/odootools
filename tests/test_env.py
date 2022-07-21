import sys
import toml
from types import ModuleType
import pytest
from odoo_tools.odoo import Environment
from odoo_tools.compat import Path
from odoo_tools.exceptions import OdooNotInstalled
from odoo_tools.api.objects import Manifest
from unittest.mock import MagicMock

from tests.utils import (
    generate_addons,
    generate_odoo_dir,
    generate_addons_full
)


def test_check_odoo(tmp_path):
    env = Environment()

    with pytest.raises(OdooNotInstalled):
        env.check_odoo()

    assert env.package_map() == {}


def test_package_map_exists(env, tmp_path):
    package_map_file = tmp_path / 'package.toml'

    with package_map_file.open('w') as fout:
        toml.dump({'xxx': 'yyy'}, fout)

    env.context.package_map_file = package_map_file
    env.context.odoo_version = "15.0"

    new_map = {
        "xxx": "yyy",
        "ldap": "python-ldap",
    }

    assert env.package_map() == new_map


def test_package_map_not_exists(env, tmp_path):
    package_map_file = tmp_path / 'package.toml'

    env.context.package_map_file = package_map_file
    env.context.odoo_version = "10.0"

    new_map = {
    }

    assert env.package_map() == new_map


def test_env_config(tmp_path):
    env = Environment()

    env.context.odoo_rc = tmp_path / 'odoo.cfg'

    with env.config():
        env.set_config('xmlrcp_interface', 'localhost')
        env.set_config('xmlrcp_port', '8069')

    with env.config():
        assert env.get_config('xmlrcp_interface') == 'localhost'

    assert env.get_config('addons_path') is None

    env.set_config('addons_path', '1')

    assert env.get_config('addons_path') == '1'


def test_env_config_addons_path(tmp_path):
    env = Environment()

    env.context.odoo_rc = tmp_path / 'odoo.cfg'

    with env.config():
        env.set_config('addons_path', ",".join([str(tmp_path)]))

    paths = env.addons_paths()
    assert paths == {tmp_path}

    env.context.force_addons_lookup = True
    assert env.addons_paths() == set()


def test_invalid_env(tmp_path):
    env = Environment()

    assert env.modules.list() == set()

    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)

    env.context.odoo_base_path = str(odoo_dir)

    assert len(env.modules.list()) == 0

    generate_addons(addons_dir, ['a', 'b', 'c'])

    assert len(env.modules.list()) == 3
    assert set(env.modules.server_wide_modules()) == {'web', 'base'}


def test_server_wide_modules(tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True)

    env = Environment()
    env.context.odoo_base_path = str(odoo_dir)

    assert len(env.modules.list()) == 4
    assert set(env.modules.server_wide_modules()) == {'web', 'base', 'd'}


def test_addons_paths(tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True)

    env = Environment()
    env.context.odoo_base_path = str(odoo_dir)

    assert len(env.modules.list()) == 4
    assert len(env.addons_paths()) == 1

    custom_addons_dir = addons_dir / 'addons2'
    custom_addons_dir.mkdir()

    generate_addons(custom_addons_dir, ['f', 'g', 'h'])

    assert len(env.modules.list(reload=True)) == 7
    assert len(env.addons_paths()) == 2

    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()

    generate_addons(custom_dir, ['i', 'j', 'k'])

    env.context.custom_paths.add(custom_dir)

    assert len(env.modules.list(reload=True)) == 10
    assert len(env.addons_paths()) == 3

    for module in ['i', 'j', 'k', 'f', 'g', 'h']:
        assert env.modules.get(module).technical_name == module

    module_i = env.modules.get('i')
    assert module_i.path.exists() is True

    env.context.disabled_modules = {'i', 'j', 'k'}
    env.modules.remove_disabled()

    assert module_i.path.exists() is False

    for mod in env.modules.list(reload=True):
        mod.package()


def test_env_options(tmp_path):
    env = Environment()

    env.env_options()


def test_env_config_import():
    sys.modules['openerp'] = ModuleType('openerp')
    sys.modules['openerp.tools'] = ModuleType('openerp.tools')
    conf = MagicMock()
    sys.modules['openerp.tools'].config = conf

    env = Environment()

    assert env.odoo_config() == conf

    sys.modules['odoo'] = ModuleType('odoo')
    sys.modules['odoo.tools'] = ModuleType('odoo.tools')
    conf = MagicMock()
    sys.modules['odoo.tools'].config = conf

    env = Environment()

    assert env.odoo_config() == conf

    del sys.modules['odoo']
    del sys.modules['openerp']
    del sys.modules['odoo.tools']
    del sys.modules['openerp.tools']


def test_manifest_save_and_files(tmp_path):
    cur_dir = Path(tmp_path)

    env = Environment()
    env.context.custom_paths.add(cur_dir)

    generate_addons_full(
        cur_dir,
        'mod1',
        {'depends': ['web']},
        {
            "__init__.pyc": "some data",
            "models": {
                "__init__.pyc": "some data2",
            },
            "static": {
                "src": {
                    "index.html": "Index File"
                }
            }
        }
    )

    mod = env.modules.get('mod1')

    assert mod.technical_name == 'mod1'
    assert len([x for x in mod.files()]) == 2
    assert len([x for x in mod.static_assets()]) == 1


def test_manifest_from_path(tmp_path):
    cur_dir = Path(tmp_path)

    env = Environment()
    env.context.custom_paths.add(cur_dir)

    generate_addons_full(
        cur_dir,
        'mod1',
        {'depends': ['web']},
        {
            "static": {
                "src": {
                    "index.html": "Index File"
                }
            }
        }
    )

    mod = Manifest.from_path(cur_dir / 'mod1')

    assert mod.technical_name == 'mod1'
    assert mod.depends == ['web']


def test_manifest_requirements(tmp_path):
    cur_dir = Path(tmp_path)

    env = Environment()
    env.context.custom_paths.add(cur_dir)

    generate_addons_full(
        cur_dir,
        'mod1',
        {'depends': ['web']},
        {
            "static": {
                "src": {
                    "index.html": "Index File"
                }
            }
        }
    )

    mod = Manifest.from_path(cur_dir / 'mod1')
    assert mod.requirements() == set()

    mod.external_dependencies['python'] = ['cryptography']
    assert mod.requirements() == {'cryptography'}

    mod.save()
    mod = Manifest.from_path(cur_dir / 'mod1')
    assert mod.requirements() == {'cryptography'}
    assert mod.requirements({'cryptography': 'crypto'}) == {'crypto'}
    assert mod.requirements({'cryptography': ''}) == set()
