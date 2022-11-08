import click
import logging

from ..odoo import Environment
from .registry import registry


@click.group()
@click.option(
    '-c',
    '--config',
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
)
@click.option(
    '--exclude-odoo',
    is_flag=True,
    help="Exclude odoo paths from results",
    default=False
)
@click.option('--log-level')
@click.pass_context
def command(ctx, config, log_level, exclude_odoo):
    ctx.ensure_object(dict)
    env = Environment()

    if config:
        env.context.odoo_rc = config

    if exclude_odoo:
        env.context.exclude_odoo = exclude_odoo

    ctx.obj['env'] = env

    if log_level:
        logging.basicConfig(level=log_level)


registry.set_main(command)
registry.load()
