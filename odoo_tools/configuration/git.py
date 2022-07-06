from six import ensure_binary, ensure_str
from subprocess import PIPE
from .misc import run, cd
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
import giturlparse
import os

import logging
from odoo_tools.compat import Path
from cryptography.fernet import Fernet
from contextlib import contextmanager

_logger = logging.getLogger(__name__)


@contextmanager
def ssh_command(addon, decrypt_key=None):
    old_command_exists = 'GIT_SSH_COMMAND' in os.environ
    old_command = os.environ.get('GIT_SSH_COMMAND')
    command_set = False

    if addon.private_key:
        key_data = ensure_binary(addon.private_key)

        # Decrypt key if possible
        if decrypt_key:
            fernet = Fernet(decrypt_key)
            key_data = fernet.decrypt(key_data)

        with TemporaryDirectory() as tempdir:
            key_dir = Path(tempdir)
            key_file = key_dir / 'key.pem'
            with key_file.open('wb') as keyfd:
                keyfd.write(key_data)

            os.chmod(str(key_file), 0o600)

            os.environ['GIT_SSH_COMMAND'] = 'ssh -i {}'.format(key_file)
            command_set = True

            yield
    else:
        yield

    if old_command_exists:
        os.environ['GIT_SSH_COMMAND'] = old_command
    elif command_set:
        del os.environ['GIT_SSH_COMMAND']


def fetch_addons(addon, output_directory, decrypt_key=None, credentials=None):
    if credentials is None:
        credentials = {}

    origin_url = addon.url

    parsed = giturlparse.parse(origin_url)

    host = parsed.host
    url_scheme = parsed.protocol

    if (
        (url_scheme == 'ssh' or addon.auth) and
        host in credentials
    ):
        credential = credentials.get(host)
        username = credential['username']
        password = credential['password']

        url = urlparse(parsed.url2https)
        url = url._replace(
            netloc="{}:{}@{}".format(
                username,
                password,
                host
            )
        ).geturl()
    else:
        url = origin_url

    _logger.info("Fetching %s", url)

    repo_path = Path.cwd() / output_directory / addon.repo_path

    repo_path.mkdir(exist_ok=True, parents=True)

    with cd(repo_path):
        run(['git', 'init'], check=False)
        run(['git', 'remote', 'add', 'origin', url], check=False)

        ref = addon.ref

        with ssh_command(addon, decrypt_key=decrypt_key):
            if ref:
                run(['git', 'fetch', 'origin', ref])
            else:
                run(['git', 'fetch', 'origin'])

        run(['git', 'checkout', 'FETCH_HEAD'])
        run(['git', 'remote', 'remove', 'origin'], check=False)

        commit_id = run(
            ['git', 'log', '--pretty=%H', '-1', 'FETCH_HEAD'],
            stdout=PIPE
        )

    return repo_path, {
        "url": url,
        "commit": ensure_str(commit_id).replace('\n', '')
    }


def checkout_repo(src, dest):
    env = dict(os.environ)
    env['GIT_WORK_TREE'] = str(dest)

    dest.mkdir(exist_ok=True, parents=True)

    _logger.info("Copying %s to %s", src, dest)

    with cd(src):
        run(
            ['git', 'checkout', '-f', 'FETCH_HEAD'],
            env=env
        )
        commit_id = run(
            ['git', 'log', '--pretty=%H', '-1'], stdout=PIPE
        )

    return commit_id
