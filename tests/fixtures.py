import sys
import pytest
import subprocess
from mock import MagicMock
from odoo_tools.odoo import Environment

from tests.utils import generate_addons


@pytest.fixture
def env(tmp_path):
    odoo_env = Environment()
    odoo_env.context.odoo_rc = tmp_path / 'odoo.cfg'
    yield odoo_env


@pytest.fixture
def addons_path(env, tmp_path):
    addons_path = tmp_path / 'addons'
    addons_path.mkdir(parents=True, exist_ok=True)

    generate_addons(addons_path, ['a', 'b', 'c'], depends=['base'])
    generate_addons(addons_path, ['d'], depends=['a'])

    env.context.custom_paths.add(addons_path)

    yield addons_path


def odoo_cleanup(env):
    print("tearing down")
    odoo_path = env.path()

    subprocess.run(['pip', 'uninstall', '-y', 'odoo'])

    odoo_modules = [
        key
        for key in sys.modules.keys()
        if key.startswith('odoo.')
    ]

    for mod in odoo_modules:
        del sys.modules[mod]

    subprocess.run(['rm', '-rf', str(odoo_path)])


@pytest.fixture(scope="module")
def odoo_env():
    env = Environment()

    options = MagicMock()

    options.languages = "fr_CA"
    options.upgrade = False
    options.target = False
    options.cache = False

    env.manage.install_odoo('15.0', opts=options)

    try:
        yield env
    finally:
        odoo_cleanup(env)


@pytest.fixture(scope="module")
def odoo_release():
    env = Environment()
    options = MagicMock()

    options.languages = "fr_CA"
    options.upgrade = False
    options.target = False
    options.cache = False

    env.manage.install_odoo('15.0', release="20220624", opts=options)

    try:
        yield env
    finally:
        odoo_cleanup(env)
