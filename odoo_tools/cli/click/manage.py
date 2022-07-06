import click
import logging
from .utils import MODULE_TYPE
from ...compat import Path

from ...configuration.misc import DictObject


_logger = logging.getLogger(__name__)


@click.group()
def manage():
    pass


@manage.command(
    help="Initialize a database with modules and some configurations."
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
    '--with-demo',
    help="Generate new database with demo",
    is_flag=True,
    default=False
)
@click.option(
    '--country',
    help="Country two letter code",
)
@click.option(
    '-l',
    '--language',
    help="Languages to use",
    multiple=True
)
@click.pass_context
def init(ctx, database, modules, country, language, with_demo):
    env = ctx.obj['env']
    env.check_odoo()
    manage = env.manage.db(database)

    manage.default_entrypoints()

    if not language:
        language = ['en_US']

    to_install = {
        mod
        for mods in modules
        for mod in mods
    }

    manage.init(
        to_install,
        country=country,
        without_demo=not with_demo,
        language=",".join(language)
    )

    return True


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

    if not languages:
        opts.languages = "all"
    else:
        opts.languages = languages

    if upgrade:
        opts.upgrade = True

    if target:
        opts.target = Path.cwd() / target

    env.manage.install_odoo(
        version,
        release=release,
        ref=ref or version,
        repo=repo,
        opts=opts
    )
