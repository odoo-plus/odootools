import json
import giturlparse
import click
import toml
import logging

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
    with Path(service_file).open('r') as fin:
        data = toml.load(fin)

    manifests = ServiceManifests.parse(data)

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
    with Path(service_file).open('r') as fin:
        data = toml.load(fin)

    manifests = ServiceManifests.parse(data)

    service = manifests.services.get(environment)
    resolved_service = service.resolved

    if cache:
        fetch_path = cache
    else:
        fetch_path = target

    results = []

    for key, addon in resolved_service.addons.items():
        if not giturlparse.parse(addon.url).valid:
            _logger.info(
                "Skipping addon %s as it has an invalid url.", addon.url
            )
            continue

        target_path = Path.cwd() / target / addon.repo_path

        path, info = fetch_addons(addon, fetch_path, decrypt_key=decrypt_key)

        if fetch_path != target_path:
            checkout_repo(path, target_path)

        results.append(info)
