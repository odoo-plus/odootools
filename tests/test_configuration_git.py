import pytest
import os
from mock import patch
from cryptography.fernet import Fernet

from odoo_tools.configuration.git import ssh_command, fetch_addons
from odoo_tools.services.objects import ServiceManifests


@pytest.fixture
def services():
    fernet_key = Fernet.generate_key()

    fernet = Fernet(fernet_key)

    pk = fernet.encrypt(b"abcdef")

    services = {
        "services": [
            {
                "name": "base",
                "odoo": {
                    "version": "12.0"
                },
                "addons": [
                    {
                        "url": "git@github.com:oca/web.git"
                    },
                    {
                        "url": "git@github.com:oca/pivate.git",
                        "private_key": pk.decode()
                    },
                    {
                        "url": "git@github.com:oca/auth.git",
                        "auth": True,
                    }
                ]
            }
        ]
    }

    manifests = ServiceManifests.parse(services)

    return fernet_key, manifests


def test_ssh_command(services):
    fernet_key, manifests = services

    base_service = manifests.services['base']

    web_addons = base_service.addons['github_com_oca_web']
    private_addons = base_service.addons['github_com_oca_pivate']

    new_dict = {}

    with patch.dict(os.environ, new_dict, clear=True):
        with ssh_command(web_addons, decrypt_key=None):
            command = os.environ.get('GIT_SSH_COMMAND')
            assert command is None

        with ssh_command(private_addons, decrypt_key=fernet_key):
            command = os.environ.get('GIT_SSH_COMMAND')
            assert command.startswith('ssh -i')

        assert os.environ == {}


def test_fetch_addons(env, tmp_path, services):
    fernet_key, manifests = services

    fetch_dir = tmp_path / 'fetch_dir'

    new_dict = {}

    base_service = manifests.services['base']
    addon = base_service.addons['github_com_oca_web']

    with patch.dict(os.environ, new_dict, clear=True),\
         patch('odoo_tools.configuration.git.run') as run:

        run.return_value = "some_commit"

        with ssh_command(addon):
            path, res = fetch_addons(addon, fetch_dir)
            assert path.exists()
            assert isinstance(res, dict)
            assert res['url'] == addon.url
            assert res['commit'] == 'some_commit'


def tests_with_creds(env, tmp_path, services):
    fernet_key, manifests = services

    output_dir = tmp_path / 'fetch_dir'

    new_dict = {}

    base_service = manifests.services['base']
    addon = base_service.addons['github_com_oca_auth']

    with patch.dict(os.environ, new_dict, clear=True),\
         patch('odoo_tools.configuration.git.run') as run:

        run.return_value = "some_commit"

        creds = {
            'github.com': {
                'username': 'user',
                'password': 'password'
            }
        }

        fetch_url = "https://user:password@github.com/oca/auth.git"
        path, res = fetch_addons(addon, output_dir, credentials=creds)
        assert res['url'] == fetch_url
