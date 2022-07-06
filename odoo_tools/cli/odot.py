import click
import logging

from ..odoo import Environment

from .click.module import module
from .click.path import addons_paths
from .click.config import config
from .click.entrypoint import entrypoint
from .click.shell import shell
from .click.manage import manage
from .click.services import service
from .click.platform import platform


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


command.add_command(config)
command.add_command(addons_paths)
command.add_command(module)
command.add_command(entrypoint)
command.add_command(shell)
command.add_command(manage)
command.add_command(service)
command.add_command(platform)
