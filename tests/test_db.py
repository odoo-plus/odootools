import os
import pytest
from mock import patch, MagicMock
from odoo_tools.odoo import Environment
from odoo_tools.db import (
    fetch_db_version,
    get_tables,
    db_filter
)
from odoo_tools.api.management import ManagementApi

from tests.utils import (
    generate_addons,
    generate_odoo_dir,
    generate_addons_full
)


def test_simple_connection_info():
    env = Environment()

    connection_info = env.manage.connection_info('test')
    assert connection_info['database'] == 'test'
    assert len(connection_info) == 1

    conn_info = env.manage.connection_info('postgres://127.0.0.1/db')
    assert conn_info['dsn'] == 'postgres://127.0.0.1/db'
    assert conn_info['database'] == 'db'

    conn_info = env.manage.connection_info(
        'postgres://user1:password1@127.0.0.1'
    )
    assert conn_info['dsn'] == 'postgres://user1:password1@127.0.0.1'
    assert conn_info['database'] == 'user1'

    conn_info = env.manage.connection_info('postgres://mydb')
    assert conn_info['dsn'] == 'postgres://mydb'
    assert conn_info['database'] == 'mydb'


def test_env_connection_info():
    new_environ = {
        'ODOO_VERSION': '15',
        'ODOO_DB_HOST': 'postgres',
        'ODOO_DB_PORT': '5431',
        'ODOO_DB_USER': 'abcd',
        'ODOO_DB_PASSWORD': 'abcdef',
        'ODOO_DB_SSLMODE': 'SSLMOD'
    }
    with patch.dict(os.environ, new_environ, clear=True):
        env = Environment()
        info = env.manage.connection_info('test')

        assert info['database'] == 'test'
        assert info['user'] == 'abcd'
        assert info['host'] == 'postgres'
        assert info['port'] == '5431'
        assert info['password'] == 'abcdef'
        assert info['sslmode'] == 'SSLMOD'


def test_config_connection_info():
    env = Environment()

    with env.config() as conf:
        conf.set('options', 'db_host', 'postgres')
        conf.set('options', 'db_port', '5431')
        conf.set('options', 'db_user', 'abcd')
        conf.set('options', 'db_password', 'abcdef')
        conf.set('options', 'db_sslmode', 'SSLMOD')

    info = env.manage.connection_info('test')

    assert info['database'] == 'test'
    assert info['user'] == 'abcd'
    assert info['host'] == 'postgres'
    assert info['port'] == '5431'
    assert info['password'] == 'abcdef'
    assert info['sslmode'] == 'SSLMOD'


def test_db_connect():
    env = Environment()

    def connect_func(**kwargs):
        return kwargs

    with patch('psycopg2.connect') as connect:
        connect.side_effect = connect_func

        conn = env.manage.db_connect('test')

        assert conn['database'] == 'test'


def test_fetch_db_version():
    cursor = MagicMock()

    cursor.fetchone.return_value = ("15.0.0.1.0",)

    version = fetch_db_version(cursor)
    cursor.execute.assert_called_once()
    assert version == "15.0"

    cursor.fetchone.return_value = None
    version = fetch_db_version(cursor)
    assert version is False


def test_get_tables():
    cursor = MagicMock()

    def execute_query(query, params):
        cursor.tables = params

    cursor.execute.side_effect = execute_query
    cursor.fetchall.side_effect = lambda: cursor.tables

    result = get_tables(cursor, ['res_company'])

    assert result == ['res_company']

    cursor.execute.side_effect = execute_query
    cursor.fetchall.side_effect = lambda: []

    result = get_tables(cursor, ['res_company'])

    assert result == []


def test_db_filter():
    dbs = [
        {'name': 'funtastic.com'},
        {'name': 'example.com'},
        {'name': 'test.com'},
        {'name': 'funtastic'},
    ]

    res = db_filter(dbs, "%h", "funtastic.com")
    assert res == [{'name': 'funtastic.com'}]

    res = db_filter(dbs, "%h", "www.funtastic.com")
    assert res == []

    res = db_filter(dbs, "%d", "funtastic.com")
    assert res == [{'name': 'funtastic.com'}, {'name': 'funtastic'}]

    res = db_filter(dbs, "%d", "www.funtastic.com")
    assert res == [{'name': 'funtastic.com'}, {'name': 'funtastic'}]

    res = db_filter(dbs, "%d.com", "www.funtastic.com")
    assert res == [{'name': 'funtastic.com'}]

    res = db_filter(dbs, "%d.com", False)
    assert res == [
        {'name': 'funtastic.com'},
        {'name': 'example.com'},
        {'name': 'test.com'},
    ]


def test_get_active_dbs():
    env = Environment()
    manage = ManagementApi(env)

    cr = MagicMock()
    cr.fetchall.return_value = [('a',), ('b',)]

    conn = MagicMock()
    conn.cursor.return_value = cr

    manage.db_connect = MagicMock()
    manage.db_connect.return_value = conn

    res = manage.get_active_dbs()

    assert res == ['a', 'b']


def test_get_db_version():
    env = Environment()
    manage = ManagementApi(env)

    cr = MagicMock()

    conn = MagicMock()
    conn.cursor().return_value = cr

    manage.db_connect = MagicMock()
    manage.db_connect.return_value = conn

    with patch('odoo_tools.api.management.fetch_db_version') as db_version, \
         patch('odoo_tools.api.management.get_tables') as get_tables:
        get_tables.return_value = ['ir_module_module']
        db_version.return_value = "15.0"

        res = manage.get_db_version("test")
        assert res == {
            "name": "test",
            "version": "15.0",
            "status": "ok"
        }

        get_tables.return_value = []

        res = manage.get_db_version("test")
        assert res == {
            "name": "test",
            "status": "invalid"
        }

        get_tables.return_value = ["ir_module_module"]
        conn.cursor.side_effect = Exception("cursor failed")
        # delattr(conn.cursor(), 'return_value')
        res = manage.get_db_version("test")
        assert res == {
            "name": "test",
            "status": "invalid"
        }

        delattr(conn.cursor, 'side_effect')
        manage.db_connect.side_effect = Exception("Connection failed")
        res = manage.get_db_version("test")
        assert res == {
            "name": "test",
            "status": "missing"
        }


def test_db_list():
    env = Environment()
    manage = ManagementApi(env)

    manage.get_active_dbs = MagicMock()
    manage.get_active_dbs.return_value = [
        'example.com',
        'example2.com',
        'example.net',
    ]

    def get_db_ver(db):
        return {
            "name": db,
            "version": "15.0",
            "status": "ok"
        }

    manage.get_db_version = MagicMock()
    manage.get_db_version.side_effect = get_db_ver

    with env.config() as conf:
        conf.set('options', 'dbfilter', '%d.com')
        conf.set('options', 'db_name', 'test.com,example.com')

    lst = manage.db_list(hostname="example.com")
    assert lst == [{'name': 'example.com', 'version': '15.0', 'status': 'ok'}]

    lst = manage.db_list(hostname="example.com", include_extra_dbs=True)
    assert lst == [
        {'name': 'example.com', 'version': '15.0', 'status': 'ok'},
    ]

    def get_db_ver_invalid(db):
        return {
            "name": db,
            "version": "15.0",
            "status": "invalid"
        }

    manage.get_db_version.side_effect = get_db_ver_invalid
    lst = manage.db_list(hostname="example.com", include_extra_dbs=True)
    assert lst == [
        {'name': 'example.com', 'version': '15.0', 'status': 'invalid'},
    ]
    lst = manage.db_list(
        hostname="example.com", include_extra_dbs=True, filter_invalid=True
    )
    assert lst == [
    ]

    def get_db_ver_missing(db):
        return {
            "name": db,
            "version": "15.0",
            "status": "missing"
        }
    manage.get_db_version.side_effect = get_db_ver_missing
    lst = manage.db_list(hostname="example.com", include_extra_dbs=True)
    assert lst == [
        {'name': 'example.com', 'version': '15.0', 'status': 'missing'},
    ]
    lst = manage.db_list(
        hostname="example.com", include_extra_dbs=True, filter_invalid=True
    )
    assert lst == [
        {'name': 'example.com', 'version': '15.0', 'status': 'missing'},
    ]
    lst = manage.db_list(
        hostname="example.com", include_extra_dbs=True, filter_missing=True
    )
    assert lst == [
    ]
    lst = manage.db_list(
        hostname="example.com", include_extra_dbs=True, filter_version="15.0"
    )
    assert lst == [
        {'name': 'example.com', 'version': '15.0', 'status': 'missing'},
    ]
    lst = manage.db_list(
        hostname="example.com", include_extra_dbs=True, filter_version="14.0"
    )
    assert lst == []

    with env.config() as conf:
        conf.set('options', 'db_name', '')

    lst = manage.db_list(hostname="example.com", include_extra_dbs=True)
    assert lst == [
        {'name': 'example.com', 'status': 'missing', 'version': '15.0'}
    ]
