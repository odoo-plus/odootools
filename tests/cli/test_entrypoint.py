from mock import patch
from odoo_tools.cli.odot import command


def test_preprocess(runner):

    obj_path = 'odoo_tools.cli.click.entrypoint.execute_entrypoint'

    with patch(obj_path) as execute:
        result = runner.invoke(
            command,
            [
                'entrypoint',
                'preprocess',
            ]
        )

        execute.assert_called_once()

        assert result.exception is None
