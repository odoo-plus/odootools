import click
import sys
from ptpython.repl import embed

from ...utils import ProtectedDict
from ...exceptions import OdooNotInstalled


@click.command()
@click.option(
    '-c',
    '--config',
    help="Config file"
)
@click.option(
    '-d',
    '--db',
    help="Database name"
)
@click.argument(
    'params',
    nargs=-1,
)
@click.pass_context
def shell(ctx, config, db, params):
    odoo_env = ctx.obj['env']

    db_name = db or odoo_env.get_config('db_name')

    try:
        db = odoo_env.manage.db(db_name)
    except OdooNotInstalled:
        print("Odoo doesn't seem to be installed.")
        sys.exit(1)

    db.default_entrypoints()

    odoo_env.manage.initialize_odoo()

    with db.env() as env:
        global_vals = {}

        local_vals = ProtectedDict({
            "env": env,
            "odoo_env": odoo_env,
            "db": db,
        })

        ret = embed(global_vals, local_vals)

    sys.exit(ret)
