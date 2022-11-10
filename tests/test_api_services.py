import json
from mock import patch
from odoo_tools.odoo import Environment


def test_load_service(tmp_path):
    env = Environment()

    service_path = tmp_path / 'services.json'
    service_file = {
        "services": [
            {
                "name": "odoo",
                "odoo": {
                    "version": "15.0",
                },
                "addons": [
                    {
                        "url": "git@github.com:llacroix/odoo-tools.git",
                    }
                ]
            },
            {
                "name": "dev",
                "inherit": "odoo",
                "addons": [
                    {
                        "url": "git@github.com:llacroix/odoo-tools-rest.git",
                    }
                ]
            }
        ]
    }

    with service_path.open("w") as fout:
        fout.write(
            json.dumps(service_file)
        )

    services = env.services.get_services(service_path)

    assert 'odoo' in services.services
    assert 'dev' in services.services

    prod = services.services['odoo']
    dev = services.services['dev'].resolved

    assert len(prod.addons) == 1
    assert len(dev.addons) == 2

    with patch('odoo_tools.api.services.fetch_addons') as fa,\
         patch('odoo_tools.api.services.checkout_repo') as cr,\
         patch('odoo_tools.api.services.ZipFile') as zp:
        fa.side_effect = [('p', 'a'), ('b', 'c')]

        res = env.services.checkout(
            dev,
            str(tmp_path / 'build')
        )

        assert res == ['a', 'c']

        fa.side_effect = [('p', 'a'), ('b', 'c')]

        env.services.package(
            dev,
            str(tmp_path / 'package')
        )
