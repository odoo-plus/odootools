import json
import giturlparse
import click
import toml
import logging
from tempfile import TemporaryDirectory

from ...services.objects import ServiceManifests
from ...compat import Path
from ...configuration.git import (
    fetch_addons,
    checkout_repo
)


_logger = logging.getLogger(__name__)


@click.group('service')
def service():
    pass


@service.command('show')
@click.option(
    '--url',
    help="Default url for self"
)
@click.argument(
    'service_file',
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
)
@click.argument('env')
@click.pass_context
def show(ctx, service_file, env, url):
    oenv = ctx.obj['env']

    manifests = oenv.services.get_services(service_file)

    service = manifests.services.get(env)
    resolved_service = service.resolved

    result = resolved_service.to_dict()

    if url and 'self' in result['addons']:
        self_addons = result['addons']['self']
        self_addons['url'] = url

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True
        )
    )


@service.command('checkout')
@click.option(
    '--cache',
)
@click.option(
    '--decrypt-key',
)
@click.argument('service_file')
@click.argument('environment')
@click.argument('target')
@click.pass_context
def checkout(ctx, service_file, environment, target, cache, decrypt_key):
    env = ctx.obj['env']

    manifests = env.services.get_services(service_file)

    service = manifests.services.get(environment)
    resolved_service = service.resolved

    env.services.checkout(
        resolved_service,
        target,
        cache or target,
        decrypt_key
    )


@service.command("package")
@click.option(
    '--cache',
)
@click.option(
    '--decrypt-key',
)
@click.option(
    '-o',
    '--output',
    help="Output file"
)
@click.argument('service_file')
@click.argument('environment')
@click.pass_context
def package(ctx, cache, service_file, environment, decrypt_key, output):
    env = ctx.obj['env']

    manifests = env.services.get_services(service_file)
    service = manifests.services.get(environment)
    resolved_service = service.resolved

    results = env.services.package(
        resolved_service,
        output,
        cache,
        decrypt_key
    )
