import os
from mock import patch
from odoo_tools.modules.search import Manifest
from odoo_tools.odoo import Environment
from odoo_tools.api.context import Context


def test_requirements(tmp_path):
    addons = tmp_path / 'addons'
    mod1 = Manifest(addons / 'mod1')
    mod1.set_attribute(['external_dependencies', 'python'], ['gitpython'])
    mod1.save()

    mod2 = Manifest(addons / 'mod2')
    mod2.set_attribute(['external_dependencies', 'python'], ['barcode'])
    mod2.save()

    requirement_file = addons / 'requirements.txt'

    with requirement_file.open('w') as fout:
        fout.write("""requests""")

    env = Environment()
    env.context.custom_paths.add(addons)

    requirements = env.modules.requirements()

    assert requirements == {'gitpython', 'barcode'}

    requirements_files1 = env.requirement_files()
    requirements_files2 = env.requirement_files(lookup_requirements=True)

    assert requirements_files1 == requirements_files2

    requirement_file2 = addons / 'mod2' / 'requirements.txt'

    with requirement_file2.open('w') as fout:
        fout.write("""gitlab""")

    requirements_files3 = env.requirement_files()
    requirements_files4 = env.requirement_files(lookup_requirements=True)

    assert requirements_files2 == requirements_files3
    assert requirements_files3 != requirements_files4

    assert requirements_files4 == {requirement_file, requirement_file2}


def test_requirements_no_modules(tmp_path):
    addons = tmp_path / 'addons'
    mod1 = Manifest(addons / 'mod1')
    mod1.save()

    mod2 = Manifest(addons / 'mod2')
    mod2.save()

    requirement_file = addons / 'requirements.txt'

    with requirement_file.open('w') as fout:
        fout.write("""requests""")

    env = Environment()
    env.context.custom_paths.add(addons)
    requirement_files = env.requirement_files()

    assert requirement_files == set([requirement_file])

    requirements = env.modules.requirements(extra_paths=requirement_files)

    assert requirements == {'requests'}


def test_disabled_modules(tmp_path):
    vals = dict(
        ODOO_DISABLED_MODULES="",
    )

    with patch.dict(os.environ, vals):
        context = Context.from_env()
        env = Environment(context)
        assert list(env.modules.disabled_modules()) == []
