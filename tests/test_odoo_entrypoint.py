import os
import pytest
from mock import patch, call, MagicMock
from odoo_tools.docker.user_entrypoint import (
    get_pg_environ,
    setup_env_config,
    setup_server_wide_modules,
    wait_postgresql,
    setup_addons_paths,
    install_master_password,
    install_python_dependencies,
    call_sudo_entrypoint,
    run_command,
)

from odoo_tools.docker.sudo_entrypoint import (
    install_apt_packages,
    fix_access_rights,
    remove_sudo
)
# from contextlib import nested
from odoo_tools.odoo import Environment
from odoo_tools.api.context import Context
from tests.utils import generate_addons


def test_get_pg_environ(tmp_path):
    env = Environment()
    env.context.odoo_rc = tmp_path / 'odoo.cfg'

    params = [
        '-d', 'db1',
        '-r', 'user1',
        '--db_host', 'postgres-1',
        '--db_port', '9090'
    ]

    new_environ = {
        "VAL": "1"
    }

    with patch.dict(os.environ, new_environ, clear=True):
        environ, params = get_pg_environ(env, params)

    assert environ['PGUSER'] == 'user1'
    assert environ['PGPORT'] == '9090'
    assert environ['PGHOST'] == 'postgres-1'
    assert environ['PGDATABASE'] == 'db1'

    with env.config():
        assert env.get_config('db_user') == 'user1'
        assert env.get_config('db_name') == 'db1'
        assert env.get_config('db_host') == 'postgres-1'
        assert env.get_config('db_port') == '9090'

    assert params == [
        '-d', 'db1',
        '-r', 'user1',
        '--db_host', 'postgres-1',
        '--db_port', '9090'
    ]


def test_get_pg_environ_env_priority(tmp_path):
    env = Environment()
    env.context.odoo_rc = tmp_path / 'odoo.cfg'

    params = [
        '-d', 'db1',
        '-r', 'user1',
        '--db_host', 'postgres-1',
        '--db_port', '9090'
    ]

    new_environ = {
        "PGHOST": 'postgres-2',
        "PGUSER": "user2",
        "PGDATABASE": "db2",
        "PGPORT": "9292",
    }

    with patch.dict(os.environ, new_environ, clear=True):
        environ, params = get_pg_environ(env, params)

    assert environ['PGUSER'] == 'user2'
    assert environ['PGPORT'] == '9292'
    assert environ['PGHOST'] == 'postgres-2'
    assert environ['PGDATABASE'] == 'db2'

    with env.config():
        assert env.get_config('db_user') == 'user2'
        assert env.get_config('db_name') == 'db2'
        assert env.get_config('db_host') == 'postgres-2'
        assert env.get_config('db_port') == '9292'

    assert params == [
        '-d', 'db2',
        '-r', 'user2',
        '--db_host', 'postgres-2',
        '--db_port', '9292'
    ]


def test_get_pg_environ_no_password(env):
    params = [
    ]

    new_environ = {
        "PGPASSWORD": "9292",
    }

    with patch.dict(os.environ, new_environ, clear=True):
        environ, params = get_pg_environ(env, params)

    assert 'PGPASSWORD' not in environ

    with env.config():
        assert env.get_config('db_password') is None

    assert params == []


def test_get_pg_environ_allow_password(env):
    env.context.allow_dangerous_settings = True

    params = [
    ]

    new_environ = {
        "PGPASSWORD": "9292",
    }

    with patch.dict(os.environ, new_environ, clear=True):
        environ, params = get_pg_environ(env, params)

    assert 'PGPASSWORD' in environ
    assert environ['PGPASSWORD'] == '9292'

    with env.config():
        assert env.get_config('db_password') == '9292'

    assert params == []


def test_get_pg_environ_no_params(tmp_path):
    env = Environment()
    env.context.odoo_rc = tmp_path / 'odoo.cfg'

    params = []

    new_environ = {}

    with patch.dict(os.environ, new_environ, clear=True):
        environ, params = get_pg_environ(env, params)

    assert environ == {}
    assert params == []


def test_wait_postgres_no_connect(env):
    from psycopg2 import OperationalError

    new_environ = {
    }

    # Defaults
    with patch.dict(os.environ, new_environ, clear=True), \
         patch('psycopg2.connect') as connect, \
         patch('time.sleep') as sleep:

        connect.side_effect = OperationalError
        sleep.return_value = None

        with pytest.raises(SystemError):
            wait_postgresql()

        assert connect.call_count == 5
        assert sleep.call_count == 5

        sleep.assert_has_calls([call(1)])

    # Custom params
    with patch.dict(os.environ, new_environ, clear=True), \
         patch('psycopg2.connect') as connect, \
         patch('time.sleep') as sleep:

        connect.side_effect = OperationalError
        sleep.return_value = None

        with pytest.raises(SystemError):
            wait_postgresql(4, 10)

        assert connect.call_count == 4
        assert sleep.call_count == 4

        sleep.assert_has_calls([call(10)])


def test_wait_postgres_connect(env):
    new_environ = {
    }

    with patch.dict(os.environ, new_environ, clear=True), \
         patch('psycopg2.connect') as connect, \
         patch('time.sleep') as sleep:

        conn_mock = MagicMock()
        conn_mock.get_dsn_parameters.return_value = {
            'user': '1',
            'host': 'pos',
            'port': '5224'
        }
        connect.return_value = conn_mock
        sleep.return_value = None

        wait_postgresql()

        assert connect.call_count == 1
        assert sleep.call_count == 0
        assert new_environ == {}


def test_setup_addons_paths(env, addons_path):
    with env.config():
        assert not env.get_config('addons_path')

    setup_addons_paths(env)

    with env.config():
        assert env.get_config('addons_path') == str(addons_path)


def test_server_wide_modules(env, addons_path):
    with env.config():
        assert not env.get_config('server_wide_modules')

    setup_server_wide_modules(env)

    with env.config():
        assert env.get_config('server_wide_modules') == "base,web"


def test_server_wide_module_extra(env, addons_path):
    generate_addons(addons_path, ['server_wide'], server_wide=True)

    setup_server_wide_modules(env)

    with env.config():
        assert env.get_config('server_wide_modules') == "base,web,server_wide"


def test_master_password_file_unencrypted(env, tmp_path):
    env.context.odoo_version = "8"

    mp = tmp_path / 'master_password'

    mp_password = "mypassword"

    with mp.open('w') as fout:
        fout.write(mp_password)

    new_environ = {}

    with patch.dict(os.environ, new_environ, clear=True):
        install_master_password(env, mp)

    with env.config():
        assert env.get_config('admin_passwd') == "mypassword"


def test_master_password_file_encrypted(env, tmp_path):
    env.context.odoo_version = "11"

    mp = tmp_path / 'master_password'

    mp_password = "mypassword"

    with mp.open('w') as fout:
        fout.write(mp_password)

    new_environ = {}

    with patch.dict(os.environ, new_environ, clear=True):
        install_master_password(env, mp)

    with env.config():
        assert env.get_config('admin_passwd') is not None
        assert env.get_config('admin_passwd') != mp_password


def test_master_password_env(env, tmp_path):
    env.context.odoo_version = "8"

    mp_password = "mypassword"

    new_environ = {
        "ODOO_VERSION": "8",
        "MASTER_PASSWORD": mp_password
    }

    with patch.dict(os.environ, new_environ, clear=True):
        env.context = Context.from_env()
        install_master_password(env)

    with env.config():
        assert env.get_config('admin_passwd') == mp_password


def test_master_password_random(env, tmp_path):
    env.context.odoo_version = "8"
    env.context.show_master_password = True

    new_environ = {
        "ODOO_VERSION": "8",
        "SHOW_MASTER_PASSWORD": "TRUE",
    }

    with patch.dict(os.environ, new_environ, clear=True), \
         patch('odoo_tools.docker.user_entrypoint.random_string') as random:

        random.return_value = "mocked"

        env.context = Context.from_env()
        install_master_password(env)

    with env.config():
        assert env.get_config('admin_passwd') == "mocked"
        random.assert_has_calls([call(64)])


def test_master_password_encrypted(env, tmp_path):
    env.context.odoo_version = "12"
    env.context.show_master_password = True

    new_environ = {
        "ODOO_VERSION": "12",
    }

    with patch.dict(os.environ, new_environ, clear=True), \
         patch('odoo_tools.docker.user_entrypoint.random_string') as random, \
         patch('odoo_tools.docker.user_entrypoint.CryptContext') as crypto:

        random.return_value = "mocked"

        crypto_context = MagicMock()

        crypto_context.identify.return_value = "plaintext"
        crypto_context.encrypt.return_value = "mocked_encrypted"
        crypto_context.hash.return_value = "mocked_encrypted"

        crypto.return_value = crypto_context

        env.context = Context.from_env()
        install_master_password(env)

    with env.config():
        assert env.get_config('admin_passwd') == "mocked_encrypted"


def test_install_python_dependencies(env, tmp_path):
    env.context.requirement_file_path = tmp_path / 'requirements.txt'
    env.context.custom_paths.add(tmp_path)

    addons_path = tmp_path / 'addons'
    addons_path.mkdir()

    deps = {
        "python": ['odoo-tools']
    }

    generate_addons(
        addons_path,
        ['server_wide'],
        external_dependencies=deps
    )

    with patch('odoo_tools.docker.user_entrypoint.pipe') as pipe:
        pipe.return_value = 0
        install_python_dependencies(env)
        pipe.assert_called_once()


def test_install_python_dependencies_exceptions(env, tmp_path):
    env.context.requirement_file_path = tmp_path / 'requirements.txt'

    with patch('odoo_tools.docker.user_entrypoint.pipe') as pipe:
        pipe.return_value = 1
        with pytest.raises(Exception):
            install_python_dependencies(env)


def test_install_python_dependencies_exceptions_ignored(env, tmp_path):
    env.context.requirement_file_path = tmp_path / 'requirements.txt'
    env.context.strict_mode = False

    with patch('odoo_tools.docker.user_entrypoint.pipe') as pipe:
        pipe.return_value = 1
        install_python_dependencies(env)
        pipe.assert_called_once()


def test_call_sudo_entrypoint(env):
    with patch('odoo_tools.docker.user_entrypoint.pipe') as pipe:
        pipe.return_value = 0

        ret = call_sudo_entrypoint()
        sudo_params = ['sudo', '-H', '-E', 'odootools', 'entrypoint', 'sudo']
        pipe.assert_has_calls([call(sudo_params)])
        assert ret == 0


def test_call_run_command(env):
    with patch('odoo_tools.docker.user_entrypoint.pipe') as pipe:
        pipe.return_value = 0
        params = ['odoo']
        ret = run_command(params)
        pipe.assert_has_calls([call(params)])
        assert ret == 0


def test_no_apt_packages(env, tmp_path):
    env.context.requirement_file_path = tmp_path / 'requirements.txt'
    env.context.custom_paths.add(tmp_path)

    addons_path = tmp_path / 'addons'
    addons_path.mkdir()

    generate_addons(
        addons_path,
        ['server_wide'],
    )

    with patch('odoo_tools.docker.sudo_entrypoint.pipe') as pipe:
        install_apt_packages(env)
        pipe.assert_not_called()


def test_apt_packages(env, tmp_path):
    env.context.requirement_file_path = tmp_path / 'requirements.txt'
    env.context.custom_paths.add(tmp_path)

    addons_path = tmp_path / 'addons'
    addons_path.mkdir()

    apt_packages = addons_path / 'apt-packages.txt'

    with apt_packages.open('w') as fout:
        fout.write("git")

    generate_addons(
        addons_path,
        ['server_wide'],
    )

    with patch('odoo_tools.docker.sudo_entrypoint.pipe') as pipe:
        pipe.return_value = 0
        install_apt_packages(env)
        assert pipe.call_count == 2


def test_apt_packages_exceptions(env, tmp_path):
    env.context.requirement_file_path = tmp_path / 'requirements.txt'
    env.context.custom_paths.add(tmp_path)

    addons_path = tmp_path / 'addons'
    addons_path.mkdir()

    apt_packages = addons_path / 'apt-packages.txt'

    with apt_packages.open('w') as fout:
        fout.write("git")

    generate_addons(
        addons_path,
        ['server_wide'],
    )

    with patch('odoo_tools.docker.sudo_entrypoint.pipe') as pipe:
        pipe.side_effect = [1]
        with pytest.raises(SystemError):
            install_apt_packages(env)

        pipe.side_effect = [0, 1]
        with pytest.raises(SystemError):
            install_apt_packages(env)


def test_env_reset_access_rights(env, tmp_path):
    new_environ = {
        "RESET_ACCESS_RIGHTS": "",
    }

    with patch.dict(os.environ, new_environ, clear=True), \
         patch('odoo_tools.docker.sudo_entrypoint.pipe') as pipe:

        env.context = Context.from_env()

        fix_access_rights(env)

        pipe.assert_not_called()

    new_environ = {
        "RESET_ACCESS_RIGHTS": "TRUE",
    }

    with patch.dict(os.environ, new_environ, clear=True), \
         patch('odoo_tools.docker.sudo_entrypoint.pipe') as pipe:

        env.context = Context.from_env()

        fix_access_rights(env)

        assert pipe.call_count == 2


def test_remove_sudo(env, tmp_path):
    with patch('odoo_tools.docker.sudo_entrypoint.pipe') as pipe:
        remove_sudo()
        pipe.assert_called_once()
