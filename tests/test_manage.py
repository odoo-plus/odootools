import pytest
from odoo_tools.modules.search import Manifest
from odoo_tools.odoo import Environment
from odoo_tools.exceptions import OdooNotInstalled


def test_packages(tmp_path):
    addons = tmp_path / 'addons'
    mod1 = Manifest(addons / 'mod1')
    mod1.set_attribute(['external_dependencies', 'python'], ['gitpython'])
    mod1.save()

    mod2 = Manifest(addons / 'mod2')
    mod2.set_attribute(['external_dependencies', 'python'], ['barcode'])
    mod2.save()

    env = Environment()
    env.context.custom_paths.add(addons)
    env.context.extra_apt_packages = {"python3"}

    package_file = addons / 'apt-packages.txt'

    with package_file.open('w') as fout:
        fout.write("""git
vim""")

    packages = env.manage.packages()

    assert packages == {"git", "vim", "python3"}


def test_management_config():
    env = Environment()
    with pytest.raises(OdooNotInstalled):
        env.manage.config


def test_management_options():
    env = Environment()
    assert isinstance(env.manage.options, dict)


def test_management_native_packages():
    env = Environment()
    default_packages = env.manage.native_packages("default")
    assert len(default_packages) > 0

    packages = env.manage.native_packages()
    assert len(packages) > 0
    assert packages != default_packages
