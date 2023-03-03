from mock import patch, MagicMock
from odoo_tools.cli.odot import command
from odoo_tools.api.services import ServiceApi


def test_service_package(runner):

    with patch.object(ServiceApi, 'get_services') as get_services, \
         patch.object(ServiceApi, 'package') as package:
        manifests = MagicMock()
        get_services.return_value = manifests
        package.return_value = []

        result = runner.invoke(
            command,
            [
                'service',
                'package',
                'service.toml',
                'odoo',
            ]
        )

        assert result.exception is None
        manifests.services.get.assert_called_with('odoo')
        service = manifests.services.get('odoo').resolved

        package.assert_called_with(
            service,
            None,  # output
            None,  # cache
            None  # decrypt_key
        )


def test_service_checkout(runner):

    with patch.object(ServiceApi, 'get_services') as get_services, \
         patch.object(ServiceApi, 'checkout') as checkout:

        manifests = MagicMock()
        get_services.return_value = manifests

        result = runner.invoke(
            command,
            [
                'service',
                'checkout',
                '--cache', 'cache',
                '--credentials', 'a:b:c',
                'service.toml',
                'odoo',
                'addons'
            ]
        )

        assert result.exception is None
        manifests.services.get.assert_called_with('odoo')
        service = manifests.services.get('odoo').resolved

        checkout.assert_called_with(
            service,
            'addons',
            'cache',
            None,
            {
                'a': {
                    "username": "b",
                    "password": "c"
                }
            }
        )
