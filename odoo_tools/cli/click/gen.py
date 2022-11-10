import click
import logging


_logger = logging.getLogger(__name__)


@click.group()
def gen():
    pass


@gen.command()
def info():
    print("Install more modules like odoo-tools-rest")
