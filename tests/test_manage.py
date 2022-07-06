import pytest
from odoo_tools.modules.search import Manifest
from odoo_tools.odoo import Environment


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
    with pytest.raises(SystemError):
        env.manage.config()
