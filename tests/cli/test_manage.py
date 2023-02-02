from mock import patch, MagicMock
from odoo_tools.cli.odot import command
from odoo_tools.api.environment import Environment


def test_bundler(runner):

    def fake_check_odoo(self):
        self.manage = MagicMock()

    obj_path = 'odoo_tools.cli.click.manage.AssetsBundler'

    with patch(obj_path) as bundler, \
         patch.object(Environment, 'check_odoo', autospec=True) as check_odoo:

        bun_instance = MagicMock()
        bundler.return_value = bun_instance

        check_odoo.side_effect = fake_check_odoo
        # manage.return_value = MagicMock()

        result = runner.invoke(
            command,
            [
                'manage',
                'asset',
                'css',
                'base.common',
            ]
        )

        assert result.exception is None
        bun_instance.get_css.assert_called_once()
        bun_instance.get_js.assert_not_called()

        result = runner.invoke(
            command,
            [
                'manage',
                'asset',
                'js',
                'base.common',
            ]
        )
        bun_instance.get_js.assert_called_once()
