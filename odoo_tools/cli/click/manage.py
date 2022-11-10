import click
import logging
from pathlib import Path

from .utils import MODULE_TYPE
from ...configuration.misc import DictObject


_logger = logging.getLogger(__name__)


@click.group()
def manage():
    pass


@manage.command(
    help="Update specified modules in a database."
)
@click.argument("database")
@click.option(
    '-m',
    '--modules',
    type=MODULE_TYPE,
    help="Modules to install",
    multiple=True
)
@click.pass_context
def update(ctx, database, modules):
    env = ctx.obj['env']
    env.check_odoo()
    manage = env.manage.db(database)

    manage.default_entrypoints()

    to_update = {
        mod
        for mods in modules
        for mod in mods
    }

    manage.install_modules(
        to_update,
        phase="update modules",
        event="update_modules"
    )

    return True


@manage.command(
    help="Install modules in the provided database"
)
@click.argument("database")
@click.option(
    '-m',
    '--modules',
    type=MODULE_TYPE,
    help="Modules to install",
    multiple=True
)
@click.option(
    '-f',
    '--force',
    help="Force module init",
    is_flag=True,
    default=False
)
@click.pass_context
def install(ctx, database, modules, force):
    env = ctx.obj['env']
    env.check_odoo()
    manage = env.manage.db(database)

    manage.default_entrypoints()

    to_install = {
        mod
        for mods in modules
        for mod in mods
    }

    manage.install_modules(
        to_install,
        phase="Installing Modules",
        force=force,
        event="install_modules"
    )

    return True


@manage.command(
    help="Uninstall specified modules from database"
)
@click.argument("database")
@click.option(
    '-m',
    '--modules',
    type=MODULE_TYPE,
    help="Modules to install",
    multiple=True
)
@click.pass_context
def uninstall(ctx, database, modules):
    env = ctx.obj['env']
    env.check_odoo()
    manage = env.manage.db(database)

    manage.default_entrypoints()

    to_remove = {
        mod
        for mods in modules
        for mod in mods
    }

    manage.uninstall_modules(
        to_remove
    )

    return True


@manage.command(
    help="Install Odoo in the current environment."
)
@click.argument(
    "version"
)
@click.option(
    '--release',
    help="Release version from https://nightly.odoo.com",
)
@click.option(
    '--repo',
    help="Repository",
    default="https://github.com/odoo/odoo.git"
)
@click.option(
    '--ref',
    help="Git reference to fetch the code",
)
@click.option(
    '--languages',
    help="Languages to keep",
    default="all"
)
@click.option(
    '--cache',
    help="Cache directory",
)
@click.option(
    '--target',
    help="Target path in which to install",
)
@click.option(
    '--upgrade',
    help="Upgrade pip packages while installing",
    is_flag=True,
    default=False
)
@click.pass_context
def setup(
    ctx,
    version,
    release,
    repo,
    ref,
    cache,
    languages,
    target,
    upgrade
):
    env = ctx.obj['env']

    opts = DictObject()

    opts.languages = languages if languages else "all"
    opts.upgrade = True if upgrade else False
    opts.target = Path.cwd() / target if target else None
    opts.cache = Path.cwd() / cache if cache else None

    env.manage.install_odoo(
        version,
        release=release,
        ref=ref or version,
        repo=repo,
        opts=opts
    )
