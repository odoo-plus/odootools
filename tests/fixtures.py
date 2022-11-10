import os
import tempfile
import sys
import pytest
from click.testing import CliRunner
import subprocess
from pathlib import Path
from mock import MagicMock
from odoo_tools.odoo import Environment
from odoo_tools.utilities.logging import (
    ignore_odoo_warnings,
    ignore_default_warnings
)
from odoo_tools.patch import unload_modules
from odoo_tools.exceptions import OdooNotInstalled

from tests.utils import generate_addons


@pytest.fixture
def env(tmp_path):
    odoo_env = Environment()
    odoo_env.context.odoo_rc = tmp_path / 'odoo.cfg'

    yield odoo_env

    config = Path(odoo_env.context.odoo_rc)

    if config.exists():
        config.unlink()


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

    # Remove odoo config
    if Path(env.context.odoo_rc).exists():
        Path(env.context.odoo_rc).unlink()

    # Remove odoo
    subprocess.run(['pip', 'uninstall', '-y', 'odoo'])
    subprocess.run(['rm', '-rf', str(odoo_path)])

    # Unload odoo
    unload_modules("odoo")


@pytest.fixture(scope="module")
def odoo_env():
    env = Environment()

    options = MagicMock()

    options.languages = "fr_CA"
    options.upgrade = False
    options.target = None
    options.cache = None

    odoo_version = "{}.0".format(os.environ['TEST_ODOO'])

    env.manage.install_odoo(odoo_version, opts=options)

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
    options.target = None
    options.cache = None

    odoo_version = "{}.0".format(os.environ['TEST_ODOO'])

    env.manage.install_odoo(odoo_version, release="20221019", opts=options)

    try:
        yield env
    finally:
        odoo_cleanup(env)


@pytest.fixture(autouse=True)
def change_test_dir(request, monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        # monkeypatch.chdir(request.fspath.dirname)
        monkeypatch.chdir(temp_dir)
        yield


@pytest.fixture(autouse=True)
def ignore_warnings(request):
    ignore_odoo_warnings()
    ignore_default_warnings()


@pytest.fixture
def runner():
    return CliRunner()
