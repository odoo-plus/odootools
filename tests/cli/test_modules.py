from mock import patch, MagicMock
from odoo_tools.cli.odot import command
from odoo_tools.api.environment import Environment

from odoo_tools.api.modules import ModuleApi
from odoo_tools.api.objects import Manifest


def test_module_deps(runner, tmp_path):

    with patch.object(ModuleApi, 'list') as list_modules:

        list_modules.return_value = [
            Manifest(tmp_path / 'a', attrs={'version': 1, 'depends': {}}),
            Manifest(tmp_path / 'b', attrs={'version': 1, 'depends': {'a'}}),
            Manifest(tmp_path / 'c', attrs={'version': 1, 'depends': {'b'}}),
            Manifest(
                tmp_path / 'd',
                attrs={
                    'version': 1,
                    'depends': {'a', 'c'}
                }
            )
        ]

        result = runner.invoke(
            command,
            [
                'module',
                'deps',
                '--only-name',
                '--exclude-modules',
                '--csv-modules', 'c,d',
            ]
        )

        modules = set(result.stdout.strip().split('\n'))
        assert modules == {'a', 'b'}

        result = runner.invoke(
            command,
            [
                'module',
                'deps',
                '--only-name',
                '--csv-modules', 'c,d',
            ]
        )
        modules = set(result.stdout.strip().split('\n'))
        assert modules == {'a', 'b', 'c', 'd'}
