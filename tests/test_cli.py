import toml
import json
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

import os
from odoo_tools.cli.odot import command
# from odoo_tools.cli import fetch_addons, copy_addons


@pytest.fixture
def runner():
    return CliRunner()


def test_command():
    with pytest.raises(SystemExit):
        command()


def test_shell(runner):
    with patch('ptpython.repl.embed') as mocked_func:
        mocked_func.return_value = 10
        result = runner.invoke(command, ["shell", "testdb"])
        msg = "Odoo doesn't seem to be installed. Check your path\n"
        assert not result.exception
        assert result.output == msg


def test_list_modules(runner, tmp_path):
    result = runner.invoke(command, ['module', 'ls'])
    assert not result.exception
    assert result.output == ""


def test_list_modules2(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True)

    with patch.dict(os.environ, {'ODOO_BASE_PATH': str(odoo_dir)}):
        result = runner.invoke(command, ['module', 'ls', '--only-name'])

    assert not result.exception
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == {'a', 'b', 'c', 'd'}


def test_list_modules_installable(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True, installable=False)

    with patch.dict(os.environ, {'ODOO_BASE_PATH': str(odoo_dir)}):
        result = runner.invoke(
            command,
            ['module', 'ls', '--only-name', '--installable']
        )

    assert not result.exception
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == {'a', 'b', 'c'}

    with patch.dict(os.environ, {'ODOO_BASE_PATH': str(odoo_dir)}):
        result = runner.invoke(
            command,
            ['module', 'ls', '--only-name', '--non-installable']
        )

    assert not result.exception
    modules = set(x for x in result.output.split('\n') if x)
    assert modules == {'d'}


def test_show_modules(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True, installable=False)

    with patch.dict(os.environ, {'ODOO_BASE_PATH': str(odoo_dir)}):
        result = runner.invoke(
            command,
            ['module', 'show', 'd']
        )

    assert isinstance(result.exception, SystemExit)

    with patch.dict(os.environ, {'ODOO_BASE_PATH': str(odoo_dir)}):
        result = runner.invoke(
            command,
            ['module', 'show', 'a']
        )

    expected_data = {
        'application': False,
        'data': [],
        'demo': [],
        'depends': ['web'],
        'description': 'a',
        'external_dependencies': {},
        'installable': True,
        'name': 'a',
        'technical_name': 'a',
        'version': '0.0.0',
    }

    data = json.loads(result.output)
    assert data == expected_data


def generate_odoo_dir(tmp_path):
    odoo_dir = tmp_path / "odoo"
    odoo_dir.mkdir()
    addons_dir = odoo_dir / "addons"
    addons_dir.mkdir()

    return odoo_dir, addons_dir


def generate_addons(addons_dir, modules, **kw):
    for module in modules:
        mod_dir = addons_dir / module
        mod_dir.mkdir()

        manifest = mod_dir / '__manifest__.py'

        with manifest.open('w') as man:
            module_dict = {
                "description": module,
                "depends": ["web"]
            }

            for key, value in kw.items():
                module_dict[key] = value

            man.write(repr(module_dict))


def test_requirements(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'])
    generate_addons(addons_dir, ['d'], server_wide=True, installable=False)
    generate_addons(
        addons_dir, ['e'], external_dependencies={'python': ['requests']}
    )
    generate_addons(
        addons_dir, ['f'], external_dependencies={'python': ['Pillow']}
    )
    with patch.dict(os.environ, {'ODOO_BASE_PATH': str(odoo_dir)}):
        result = runner.invoke(
            command,
            ['module', 'requirements', '--sort']
        )

    assert result.output == "pillow\nrequests\n"


def test_deps(runner, tmp_path):
    odoo_dir, addons_dir = generate_odoo_dir(tmp_path)
    generate_addons(addons_dir, ['a', 'b', 'c'], depends=[])
    generate_addons(addons_dir, ['d'], depends=['a'])
    generate_addons(addons_dir, ['e'], depends=['b'])
    generate_addons(addons_dir, ['z'], depends=['c'])
    generate_addons(addons_dir, ['f'], depends=['e', 'd', 'z'])
    generate_addons(addons_dir, ['h'], depends=['b'], auto_install=True)
    generate_addons(addons_dir, ['g'], depends=['f', 'h'], auto_install=True)
    with patch.dict(os.environ, {'ODOO_BASE_PATH': str(odoo_dir)}):
        result = runner.invoke(
            command,
            ['module', 'deps', '-m', 'f', '--auto', '--only-name', '--csv']
        )

    assert result.output == "a,b,c,d,e,h,z,g"


def test_service(runner, tmp_path):
    services = {
        "services": [
            {
                "name": "base",
                "addons": [
                    {
                        "url": "https://github.com/oca/web.git",
                    },
                    {
                        "url": "self",
                        "branch": "12.0-tests"
                    }
                ]
            },
            {
                "name": "test",
                "inherit": "base",
                "odoo": {
                    "version": "12.0",
                    "repo": {
                        "url": "https://github.com/odoo/odoo.git",
                    }
                },
                "addons": [
                    {
                        "url": "https://github.com/oca/knowledge.git"
                    }
                ]
            }
        ]
    }

    manifest_toml = tmp_path / 'services.toml'

    with manifest_toml.open('w') as fout:
        toml.dump(services, fout)

    result = runner.invoke(
        command,
        [
            'service',
            'show',
            '--url', 'https://github.com/llacroix/addons.git',
            str(manifest_toml),
            "test"
        ],
    )

    assert result.exception is None

    output = json.loads(result.output)

    out_data = {
        "name": "test",
        "odoo": {
            "version": "12.0",
            "repo": {
                "url": "https://github.com/odoo/odoo.git",
                'branch': None,
                'commit': None,
                'private_key': None,
                'ref': '12.0',
            },
            "options": {}
        },
        "env": {},
        "labels": {},
        "addons": {
            "github_com_oca_web": {
                "url": "https://github.com/oca/web.git",
                'branch': None,
                'commit': None,
                'private_key': None,
                'ref': '12.0',
            },
            "github_com_oca_knowledge": {
                "url": "https://github.com/oca/knowledge.git",
                'branch': None,
                'commit': None,
                'private_key': None,
                'ref': '12.0',
            },
            "self": {
                "url": "https://github.com/llacroix/addons.git",
                'branch': "12.0-tests",
                'commit': None,
                'private_key': None,
                'ref': '12.0-tests',
            }
        }
    }

    assert output == out_data


def test_odot_platform(runner, tmp_path):
    result = runner.invoke(
        command,
        [
            'platform',
            'arch'
        ],
    )

    assert result.output == "amd64"


def test_config(env, tmp_path, runner):
    odoo_rc_path = tmp_path / 'odoo.cfg'

    envs = {
        'ODOO_RC': str(odoo_rc_path)
    }

    runner.env = envs

    result = runner.invoke(
        command,
        [
            'config',
            'get',
            'data_dir'
        ],
        env=envs,
    )

    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'config',
            'set',
            'data_dir',
            'value'
        ],
        env=envs,
    )

    assert result.output == ""

    result = runner.invoke(
        command,
        [
            'config',
            'get',
            'data_dir',
        ],
        env=envs,
    )

    assert result.output == "value\n"

    result = runner.invoke(
        command,
        [
            'config',
            'ls',
        ]
    )
    assert result.output == "options.data_dir = value\n"
