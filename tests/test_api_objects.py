import pytest
from pathlib import Path
from odoo_tools.api.objects import CompanySpec, Manifest

fake_files = {
    "__init__.py": """
from . import models
from . import controllers
""",
    "models/__init__.py": """
from . import sale_obj
""",
    "models/sale_obj": """
from odoo import models

class MyObj(models.Model):
    _name = "my.obj"
""",
    "controllers/__init__.py": """
from . import main
""",
    "controllers/main.py": """
from odoo.http import Controller

class MyController(Controller):
    @http.route()
    def whoa():
        return ""
"""
    }


def test_company_spec():
    company = CompanySpec(country_code='CA')
    assert company.country_code == 'CA'


def test_custom_empty_manifest(tmp_path):
    manifest = Manifest(tmp_path / 'sup')

    assert manifest.technical_name == 'sup'

    assert manifest.depends == []
    assert manifest.demo == []
    assert manifest.data == []
    assert manifest.application is False
    assert manifest.installable is True
    assert manifest.version == "0.0.0"
    assert manifest.external_dependencies == dict()

    assert manifest._manifest_file == manifest.path / '__manifest__.py'
    assert manifest.static_assets() == []

    manifest.name = "some name"

    manifest.save()

    manifest = Manifest.from_path(manifest.path)
    assert manifest.name == "some name"


def test_openerp_manifest(tmp_path):
    description = """
Some module
===========

some module description
"""

    manifest = {
        "name": "module_name",
        "summary": "summary",
        "depends": ['web', 'base'],
        "description": description
    }

    module_path = tmp_path / 'mod'
    module_path.mkdir()

    html_file = module_path / 'static/description/index.html'

    html_file.parent.mkdir(parents=True)

    with html_file.open('w') as index:
        index.write("""<!doctype html>
<html>
<head>
    <link src="style.css" rel="stylesheet" type="text/css" />
</head>
<body>
    <div></div>
</body>
</html>
""")

    manifest_file = module_path / '__openerp__.py'

    with manifest_file.open('w') as fout:
        fout.write(repr(manifest))

    manifest = Manifest.from_path(module_path, render_description=True)

    assert manifest.name == "module_name"
    assert manifest.summary == "summary"
    assert manifest.depends == ['web', 'base']
    assert manifest.installable is True

    manifest.disable()

    assert manifest.installable is False

    manifest.save()

    manifest = Manifest.from_path(module_path, render_description=True)
    assert manifest.installable is False


def test_manifest_set_attribute(tmp_path):
    manifest = Manifest(tmp_path / 'sup')

    manifest.set_attribute(
        ['external_dependencies', 'python'],
        ['web', 'base', 'fun']
    )

    deps = manifest.external_dependencies['python']
    assert deps == ['web', 'base', 'fun']

    assert manifest == Path('a/b/sup')


def test_invalid_manifest(tmp_path):
    manifest = Manifest(tmp_path / 'sup')
    manifest.save()

    with manifest._manifest_file.open('wb') as fout:
        fout.write('{"depends": base, web}'.encode())

    with pytest.raises(SyntaxError):
        manifest = Manifest.from_path(manifest.path)


def test_manifest_checksum(tmp_path):
    module_path = tmp_path / 'sup'

    manifest = Manifest(tmp_path / 'sup')

    manifest.set_attribute(
        ['external_dependencies', 'python'],
        ['web', 'base', 'fun']
    )

    manifest.save()

    main_controller = module_path / 'controllers/main.py'
    manifest_file = module_path / '__manifest__.py'

    # Add file to generate valid module
    for filename, data in fake_files.items():
        file_path = module_path / filename
        file_path.parent.mkdir(exist_ok=True, parents=True)
        with file_path.open('w') as fout:
            fout.write(data)
    checksum = manifest.checksum()
    assert checksum.hexdigest() == "01f34218933d0cc173a1cac18ca6c96779901de9"

    # Ensure that sub file modified changes checksum
    with main_controller.open('w') as fout:
        fout.write("import odoo\n")
    checksum = manifest.checksum()
    assert checksum.hexdigest() == "006236cde58f9110ccfc1aea264bee2da8c3fc1f"

    # Check that manifest is part of the file
    with manifest_file.open('w') as fout:
        fout.write('{}')
    checksum = manifest.checksum()
    assert checksum.hexdigest() == "f7daa17811c84315adf726ad7e6a026943b48a22"
