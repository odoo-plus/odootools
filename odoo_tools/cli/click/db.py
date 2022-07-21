import click
import logging
from .utils import MODULE_TYPE


_logger = logging.getLogger(__name__)


@click.group()
def db():
    pass


@db.command(
    help="Get database list",
)
@click.option(
    '--filter-missing',
    is_flag=True,
    default=False
)
@click.option(
    '--filter-invalid',
    is_flag=True,
    default=False
)
@click.option(
    '--filter-version',
    default='current'
)
@click.option(
    '--include-extra-dbs',
    default=False,
    is_flag=True,
    help="Include databases not present in db_name"
)
@click.option(
    '-d',
    '--db-name',
    help="explicit db_name value ignores config value"
)
@click.option(
    '--dbfilter',
    help="explicit dbfilter"
)
@click.option(
    '--hostname',
)
@click.pass_context
def list(
    ctx,
    filter_missing,
    filter_version,
    filter_invalid,
    include_extra_dbs,
    hostname,
    db_name,
    dbfilter
):
    env = ctx.obj['env']

    if filter_version == 'current':
        version = env.odoo_version()

        if version:
            filter_version = "{}.0".format(version)
        else:
            filter_version = False

    if filter_version == 'any':
        filter_version = False

    dbs = env.manage.db_list(
        db_name=db_name,
        dbfilter=dbfilter,
        hostname=hostname,
        filter_missing=filter_missing,
        filter_version=filter_version,
        filter_invalid=filter_invalid,
        include_extra_dbs=include_extra_dbs,
    )

    for db in dbs:
        print(db['name'])


@db.command(
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
