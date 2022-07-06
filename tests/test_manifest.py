import pytest
from odoo_tools.modules.search import Manifest
from odoo_tools.compat import Path
from odoo_tools.modules.search import get_manifest, find_modules_paths
from odoo_tools.api.objects import try_compile_manifest
from odoo_tools.exceptions import ArgumentError
from six import ensure_binary, ensure_text

import mock
from io import BytesIO, StringIO


fake_manifest_1 = """# coding: utf-8
# SOme comment
{
    "name": "Some",
    "depends": ["web", "base"],
    "version": "0.1",
}
"""

fake_manifest_2 = ensure_binary(fake_manifest_1)

no_name_manifest = """
{
  "depends": ["sale"],
}
"""


def test_manifest():
    manifest = Manifest('test', {})

    assert manifest.installable is True
    assert manifest.application is False
    assert manifest.depends == []
    assert manifest.version == "0.0.0"
    assert manifest.external_dependencies == {}
    assert manifest.path == Path("test")


def test_manifest_with_data():
    data = {
        "name": "Fun",
        "description": "Description",
        "installable": False,
        "application": True,
        "version": "0.1",
        "external_dependencies": {
            "python": ["gitpython"]
        },
        "depends": ["web", "sale"]
    }

    manifest = Manifest("test2", data)

    assert manifest.depends == ["web", "sale"]
    assert manifest.external_dependencies == {"python": ["gitpython"]}
    assert manifest.version == "0.1"
    assert manifest.installable is False
    assert manifest.application is True
    assert manifest.name == "Fun"


def test_read_string_manifest():
    """ test manifest read from string """
    fake_manifest = StringIO(ensure_text(fake_manifest_1))
    with mock.patch('odoo_tools.compat.Path.exists', return_value=True):
        with mock.patch(
            'odoo_tools.compat.Path.open',
            return_value=fake_manifest
        ):
            manifest = get_manifest(Path("my_modules/__manifest__.py"))

            assert manifest.name == "Some"
            assert manifest.technical_name == "my_modules"
            assert manifest.version == "0.1"


def test_read_bytes_manifest():
    """ Test a manifest read from bytes """
    fake_manifest = BytesIO(ensure_binary(fake_manifest_2))
    with mock.patch('odoo_tools.compat.Path.exists', return_value=True):
        with mock.patch(
            'odoo_tools.compat.Path.open',
            return_value=fake_manifest
        ):
            manifest = get_manifest(Path("my_modules/__manifest__.py"))

            assert manifest.name == "Some"
            assert manifest.technical_name == "my_modules"
            assert manifest.version == "0.1"


def test_noname():
    """Test a manifest without name or version"""
    fake_manifest = StringIO(ensure_text(no_name_manifest))

    with mock.patch('odoo_tools.compat.Path.exists', return_value=True):
        with mock.patch(
            'odoo_tools.compat.Path.open',
            return_value=fake_manifest
        ):
            manifest = get_manifest(Path("my_modules/__manifest__.py"))

            assert manifest.name == "my_modules"
            assert manifest.technical_name == "my_modules"
            assert manifest.depends == ['sale']
            assert manifest.version == "0.0.0"


def test_find_modules(tmp_path):
    paths = [
        "a/b/__init__.py",
        "a/b/__manifest__.py",
        "a/c/__init__.py",
        "a/c/__openerp__.py",
        ".git/a/b/d",
        ".git/a/e/d",
        ".git/a/e/f",
        ".git/a/e/g",
        "a/d/e/__init__.py",
        "a/d/e/__manifest__.py"
    ]

    for path in paths:
        pp = tmp_path / Path(path)

        if pp.name.endswith('.py'):
            pp.parent.mkdir(parents=True, exist_ok=True)
            pp.open('w').write(ensure_text(fake_manifest_1))
        else:
            pp.mkdir(parents=True, exist_ok=True)

    modules = find_modules_paths([tmp_path])
    assert len(modules) == 3


def test_manifest_operators(tmp_path):
    man1 = Manifest(tmp_path / 'a')
    man2 = Manifest(tmp_path / 'a')
    man3 = Manifest(tmp_path / 'b')
    man4 = Manifest(tmp_path / 'b' / 'a')

    assert (man1 == man2) is True
    assert (man1 < man3) is True
    assert (man1 < man4) is False
    assert (man1 == 'a') is True
    assert (man3 == 'b') is True
    assert (man1 == 0) is False
    assert str(man1) == str(tmp_path / 'a')
    assert repr(man1).startswith('Manifest(') is True

    vals = {
        "technical_name": "a",
        "depends": [],
        "application": False,
        "installable": True,
        "external_dependencies": {},
        "demo": [],
        "data": [],
        "version": "0.0.0",
    }

    assert man1.values() == vals

    man1.version = "1.0.0"
    vals['version'] = "1.0.0"

    assert man1.values() == vals
    man1.set_attribute(
        ['external_dependencies', 'python'],
        ['cryptography']
    )
    man1.set_attribute(
        ['external_dependencies', 'binary', 'test'],
        ['cryptography']
    )

    with pytest.raises(ArgumentError):
        man1.set_attribute([], ['cryptography'])

    vals['external_dependencies'] = {
        "python": ['cryptography'],
        "binary": {
            "test": ['cryptography']
        }
    }

    assert man1.values() == vals
    assert 'external_dependencies' in man1
    assert 'vacuum' not in man1


def test_try_eval_manifest():
    data = try_compile_manifest('{"name": "test"}')
    assert data == {"name": "test"}
