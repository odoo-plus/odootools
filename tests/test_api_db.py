from unittest.mock import patch, PropertyMock, MagicMock
from psycopg2 import OperationalError
from odoo_tools.api.db import set_missing_keys, DbApi
from odoo_tools.api.db import manage
from odoo_tools.api.environment import Environment


def test_set_missing_keys():
    config = {
        'website': True
    }

    set_missing_keys(config, 'sale', False)
    assert config == {'sale': False, 'website': True}

    set_missing_keys(config, 'stock', True)
    assert config == {'sale': False, 'stock': True, 'website': True}

    set_missing_keys(config, 'website', False)
    assert config == {'sale': False, 'stock': True, 'website': True}

    set_missing_keys(config, 'stock', False)
    assert config == {'sale': False, 'stock': True, 'website': True}

    class Config(object):
        def __init__(self):
            self.options = {}

        def __setitem__(self, key, value):
            self.options[key] = value

        def __getitem__(self, key):
            return self.options[key]

    conf = Config()
    set_missing_keys(conf, 'stock', True)

    assert conf.options == {'stock': True}


def test_unmark_modules():
    manage = MagicMock()
    dbapi = DbApi(manage, 'dbtest')

    dbapi.config = {
        'init': {
        },
        'update': {
        }
    }

    dbapi.unmark_modules()

    assert dbapi.config['init'] == {}
    assert dbapi.config['update'] == {}

    dbapi.config = {
        'init': {
            'sale': True
        },
        'update': {
            'all': True
        }
    }

    dbapi.unmark_modules()

    assert dbapi.config['init'] == {'sale': False}
    assert dbapi.config['update'] == {'all': False}


def test_mark_modules():
    def mod(name):
        module = MagicMock()
        module.name = name
        return module

    manage = MagicMock()
    dbapi = DbApi(manage, 'dbtest')
    dbapi.env = MagicMock()
    mod_mock = MagicMock()
    mod_mock.search.return_value = []
    env_mock = {
        'ir.module.module': mod_mock
    }
    dbapi.env.return_value.__enter__.return_value = env_mock

    dbapi.config = {
        'init': {
        },
        'update': {
        }
    }

    dbapi.mark_modules({'website'})

    assert dbapi.config['init'] == {'website': 1}
    assert dbapi.config['update'] == {}

    dbapi.config = {
        'init': {
        },
        'update': {
        }
    }

    mod_mock.search.return_value = [
        mod('stock')
    ]

    dbapi.mark_modules({'website', 'stock'})

    assert dbapi.config['init'] == {'website': 1}
    assert dbapi.config['update'] == {'stock': 1}

    mod_mock.search.return_value = [
        mod('stock')
    ]

    dbapi.config = {
        'init': {
        },
        'update': {
        }
    }

    dbapi.mark_modules({'stock'})

    assert dbapi.config['init'] == {}
    assert dbapi.config['update'] == {'stock': 1}

    mod_mock.search.return_value = [
        mod('stock'),
        mod('sale'),
    ]

    dbapi.config = {
        'init': {
        },
        'update': {
        }
    }

    dbapi.mark_modules({'stock', 'sale', 'website'})

    assert dbapi.config['init'] == {'website': 1}
    assert dbapi.config['update'] == {'stock': 1, 'sale': 1}


def test_mark_modules_error():
    manage = MagicMock()
    dbapi = DbApi(manage, 'dbtest')
    dbapi.env = MagicMock()
    mod_mock = MagicMock()
    env_mock = {
        'ir.module.module': mod_mock
    }
    dbapi.env.return_value.__enter__.return_value = env_mock

    dbapi.config = {
        'init': {
        },
        'update': {
        }
    }

    mod_mock.search.side_effect = Exception("Something went wrong")
    dbapi.mark_modules({'website'})
    assert dbapi.config['init'] == {}
    assert dbapi.config['update'] == {}

    mod_mock.search.side_effect = OperationalError("Something went wrong")
    dbapi.mark_modules({'website'})
    assert dbapi.config['init'] == {}
    assert dbapi.config['update'] == {}

    mod_mock.search.side_effect = KeyError("Something went wrong")
    dbapi.mark_modules({'website'})
    assert dbapi.config['init'] == {}
    assert dbapi.config['update'] == {}


def test_manage():
    manager = MagicMock()
    manager.manage.__enter__.return_value = None

    env = Environment()
    env.odoo_version = MagicMock()
    env.odoo_version.return_value = 12

    with manage(env, manager):
        manager.manage.assert_called_once()

    manager.manage.reset_mock()

    env.odoo_version.return_value = 15
    with manage(env, manager):
        manager.manage.assert_not_called()

    env.odoo_version.return_value = 14
    with manage(env):
        manager.manage.assert_not_called()
