import os
import sys
import click
import logging

from ...docker.sudo_entrypoint import (
    install_apt_packages,
    fix_access_rights,
    remove_sudo,
)

from ...docker.user_entrypoint import (
    call_sudo_entrypoint,
    install_master_password,
    setup_env_config,
    setup_server_wide_modules,
    get_pg_environ,
    setup_addons_paths,
    install_python_dependencies,
    wait_postgresql,
    run_command
)

from ...entrypoints import execute_entrypoint


_logger = logging.getLogger(__name__)


@click.group()
def entrypoint():
    pass


@entrypoint.command()
@click.pass_context
def preprocess(ctx):
    env = ctx.obj['env']

    if not env.context.skip_sudo_entrypoint:
        ret = call_sudo_entrypoint()

    execute_entrypoint('odoo_tools.preprocess', env)

    sys.exit(ret)


@entrypoint.command()
@click.argument('params', nargs=-1)
@click.pass_context
def user(ctx, params):
    env = ctx.obj['env']

    # Install apt package first then python packages
    if not env.context.skip_sudo_entrypoint:
        ret = call_sudo_entrypoint()
    else:
        ret = 0

    if ret not in [0, None]:
        return ret

    with env.config():
        if not env.context.skip_pip:
            install_python_dependencies(env)

        install_master_password(env)
        environ, params = get_pg_environ(env, params)
        os.environ.update(environ)
        setup_addons_paths(env)
        setup_server_wide_modules(env)
        setup_env_config(env)

    if not env.context.skip_postgres_wait:
        wait_postgresql()

    ret = run_command(params)
    sys.exit(ret)


@entrypoint.command()
@click.argument('params', nargs=-1)
@click.pass_context
def sudo(ctx, params):
    if os.getuid() != 0:
        _logger.error("Cannot call sudo entrypoint as user")

    env = ctx.obj['env']

    try:
        install_apt_packages(env)
        fix_access_rights(env)
        env.modules.remove_disabled()
    except SystemError:
        return remove_sudo()
        if env.context.strict_mode:
            raise

    return remove_sudo()
