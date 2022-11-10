import sys
import tempfile
import time
import os
from passlib.context import CryptContext

import logging

from ..utils import random_string
from ..compat import pipe, Path
from ..configuration.pip import pip_command


_logger = logging.getLogger(__name__)


def run_command(params):
    """
    Main process running odoo
    """
    _logger.info("Starting main command: %s", params)

    if not params or len(params) == 0:
        return 0

    return pipe(params)


def call_sudo_entrypoint():
    """
    Call the odoo-entrypoint method with sudo.

    This method exist to ensure that a few things are well
    prepared for a docker image. It call the odoo-entrypoint
    again with root access to setup things like secrets,
    apt packages and so on.

    This can only be called once as the sudo access are stripped
    after calling this method once.

    Ideally, you'd want to prepare the odoo environment at build
    time for the image. Doing that at boot time consume time for
    nothing especially if you can build complete images that have
    all dependencies with pip/apt installed before executing the
    image.

    Entrypoints are just there to simplify setting up an image
    with addons mounted volumes that are only known at runtime.
    """
    command = ["sudo", "-H", "-E"]
    args = ["odootools", "entrypoint", "sudo"]

    ret = pipe(command + args)

    return ret


def install_python_dependencies(env):
    """
    Install all the requirements.txt file found
    """
    # TODO
    # https://pypi.org/project/requirements-parser/
    # to parse all the requirements file to parse all the possible specs
    # then append the specs to the loaded requirements and dump
    # the requirements.txt file in /var/lib/odoo/requirements.txt and
    # then install this only file instead of calling multiple time pip
    # all_paths = ['/addons'] + get_extra_paths()

    requirement_files = env.requirement_files()
    requirement_files_lst = list(set(requirement_files))
    requirement_files_lst.sort()

    message = "Installing python requirements found in:\n%s"

    _logger.info(
        message,
        "    \n".join([
            str(f_path)
            for f_path in requirement_files_lst
        ])
    )

    package_map = env.package_map()

    # Convert the set to a sorted list to prevent causing
    # changes with files with the same set but in a different
    # order.
    requirements = list(env.modules.requirements(
        package_map=package_map,
        extra_paths=requirement_files,
    ))
    requirements.sort()
    data = "\n".join(requirements)

    for req_file in requirement_files:
        _logger.info("Installing python packages from %s", req_file)

    with tempfile.TemporaryDirectory() as directory:
        file_path = Path(directory) / 'requirements.txt'

        with file_path.open('w') as fout:
            _logger.info("Requirements:\n%s", data)
            fout.write(data)

        args = pip_command(user=True) + [
            "-r", str(file_path)
        ]

        retcode = pipe(args)

    if env.context.strict_mode and retcode != 0:
        raise Exception("Failed to install pip dependencies")

    _logger.info("Installing python requirements complete")


def install_master_password(
    env,
    master_password_secret_path="/run/secrets/master_password"
):
    # Secure an odoo instance with a default master password
    # if required we can update the master password but at least
    # odoo doesn't get exposed by default without master passwords
    _logger.info("Installing master password in ODOORC")

    master_password_secret = Path(
        master_password_secret_path
    )

    if master_password_secret.exists():
        with master_password_secret.open("r") as mp:
            master_password = mp.read().strip()
    elif env.context.master_password:
        master_password = env.context.master_password
    else:
        master_password = random_string(64)

        if env.context.show_master_password:
            _logger.info(
                (
                    "Use this randomly generated master password"
                    " to manage the database\n"
                    "    %s"
                ),
                master_password
            )

    # Check that we don't have plaintext and encrypt it
    # This allow us to quickly setup servers without having to hash
    # ourselves first for security reason, you should always hash
    # the password first and not expect the image to do it correctly
    # but older version of odoo do not support encryption so only encrypt
    # older version of odoo...
    ctx = CryptContext(
        ['pbkdf2_sha512', 'plaintext'],
        deprecated=['plaintext']
    )
    if (
        env.odoo_version() > 10 and
        ctx.identify(master_password) == 'plaintext'
    ):
        hash_password = (
            ctx.hash
            if hasattr(ctx, 'hash')
            else ctx.encrypt
        )
        master_password = hash_password(master_password)

    with env.config():
        env.set_config('admin_passwd', master_password)

    _logger.info("Installing master password completed")


def setup_addons_paths(env):
    with env.config():
        env.set_config('addons_path', ",".join([
            str(path) for path in env.addons_paths()
        ]))


def setup_server_wide_modules(env):
    _logger.info("Searching for server wide modules")

    server_wide_modules = env.modules.server_wide_modules()

    modules = ",".join(server_wide_modules)
    _logger.info("Setting server wide modules to %s" % (modules))
    with env.config():
        env.set_config('server_wide_modules', modules)


def setup_env_config(env):
    with env.config():
        for key, value in env.env_options().items():
            env.set_config(key, value)


def get_pg_environ(odoo_env, params):
    _logger.info("Configuring environment variables for postgresql")

    def ensure_config(env_key, param_long, param_small, odoo_config):
        """
        Check if config is in odoo_rc or command line
        """
        idx = -1
        value = False

        # First check for environment variable
        if env_key in os.environ:
            value = os.environ[env_key]

        # Then check for parameters
        if param_long and '--%s' % param_long in params:
            idx = params.index('--%s' % param_long)
            if not value:
                value = params[idx + 1] if idx < len(params) else None

        if param_small and '-%s' % param_small in params:
            idx = params.index('-%s' % param_small)
            if not value:
                value = params[idx + 1] if idx < len(params) else None

        # Then check config file
        if not value:
            value = odoo_env.get_config(odoo_config)

        return value, idx

    variables = [
        ('PGUSER', 'db_user', 'r', 'db_user'),
        ('PGHOST', 'db_host', None, 'db_host'),
        ('PGPORT', 'db_port', None, 'db_port'),
        ('PGDATABASE', 'database', 'd', 'db_name')
    ]

    # Accpet db_password only with this if some infra cannot be setup
    # otherwise...
    # It's a bad idea to pass password in cleartext in command line or
    # environment variables so please use .pgpass instead...
    if odoo_env.context.allow_dangerous_settings:
        variables.append(
            ('PGPASSWORD', 'db_password', 'w', 'db_password')
        )

    environ = {}

    # Setup basic PG env variables to simplify managements
    # combined with secret pg pass we can use psql directly
    new_params = params[:]

    with odoo_env.config():
        for env_key, param_long, param_small, odoo_config in variables:
            value, param_idx = ensure_config(
                env_key,
                param_long,
                param_small,
                odoo_config
            )

            if value:
                environ[env_key] = value
                odoo_env.set_config(odoo_config, value)

                # Override param
                if param_idx >= 0:
                    new_params[param_idx+1] = value

    _logger.info("Configuring environment variables done")

    return environ, new_params


def wait_postgresql(retry_count=None, retry_wait_time=None):
    import psycopg2

    if retry_count is None:
        retry_count = 5

    if retry_wait_time is None:
        retry_wait_time = 1

    error = None
    reset_db = False

    # Default database set to postgres
    if not os.environ.get('PGDATABASE'):
        os.environ['PGDATABASE'] = 'postgres'
        reset_db = True

    for retry in range(retry_count):
        try:
            _logger.info("Trying to connect to postgresql")
            # connect using defined env variables and pgpass files
            conn = psycopg2.connect("")
            message = "  Connected to %(user)s@%(host)s:%(port)s"
            _logger.info(message % conn.get_dsn_parameters())
            break
        except psycopg2.OperationalError as exc:
            error = exc
            time.sleep(retry_wait_time)
    else:
        # we reached the maximum retries so we trigger failure mode
        if error:
            _logger.info("Database connection failure %s", error)

        if reset_db:
            del os.environ['PGDATABASE']

        raise SystemError("Database connection failure")

    if reset_db:
        del os.environ['PGDATABASE']
