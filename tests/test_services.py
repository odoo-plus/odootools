from odoo_tools.services.objects import ServiceManifests


inheritance_services = {
    'services': [
        {
            'name': 'prod',
            'inherit': 'dev',
            'env': {
                'a': '3',
                'd': '4'
            }
        },
        {
            'name': 'prod2',
            'inherit': 'dev',
            'addons': [],
            'env': {
                'a': '3',
                'd': '4'
            }
        },
        {
            'name': 'base',
            'addons': [
                {
                    'url': 'git@github.com:example/com.git',
                    'branch': 'main'
                }
            ],
            'env': {
                'a': 'b',
                'c': 'd'
            }
        },
        {
            'name': 'dev',
            'inherit': 'base',
            'env': {
                'a': '2',
                'b': '1'
            },
            'addons': [
                {
                    'url': 'git@github.com:example/com2.git',
                    'branch': 'staging'
                },
                {
                    'url': 'git@github.com:example/com.git',
                    'branch': 'staging'
                }
            ],
        }
    ]
}


def test_no_services():
    services = {
        'services': [
        ]
    }

    parsed_services = ServiceManifests.parse(services)

    assert len(parsed_services.services) == 0


def test_basic_service():
    services = {
        'services': [
            {
                'name': 'base',
                'env': {
                    'a': 'b',
                    'c': 'd'
                }
            }
        ]
    }

    parsed_services = ServiceManifests.parse(services)

    assert len(parsed_services.services) == 1
    assert parsed_services.services['base'].name == 'base'
    assert parsed_services.services['base'].env.to_dict() == {
        'a': 'b',
        'c': 'd'
    }

    dict_vals = {
        'services': {
            'base': {
                'name': 'base',
                'env': {
                    'a': 'b',
                    'c': 'd'
                },
                'addons': {}
            }
        }
    }

    assert parsed_services.to_dict() == dict_vals


def test_service_no_inheritance():
    manifest = ServiceManifests.parse(inheritance_services)

    assert len(manifest.services) == 4
    assert manifest.services['prod'].addons is None
    assert len(manifest.services['prod2'].addons) == 0
    assert len(manifest.services['dev'].addons) == 2
    assert len(manifest.services['base'].addons) == 1

    vals = {'a': '3', 'd': '4'}
    assert manifest.services['prod'].env.to_dict() == vals


def test_service_inheritance():
    manifest = ServiceManifests.parse(inheritance_services)

    assert len(manifest.services['prod'].resolved.addons) == 2
    assert len(manifest.services['dev'].resolved.addons) == 2
    assert len(manifest.services['base'].resolved.addons) == 1

    prod_resolved = manifest.services['prod'].resolved

    vals = {'a': '3', 'd': '4', 'b': '1', 'c': 'd'}
    assert prod_resolved.env.to_dict() == vals

    assert prod_resolved.addons['github_com_example_com'].branch == 'staging'
