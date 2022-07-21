import toml
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from click.testing import CliRunner

import os
from odoo_tools.cli.odot import command
from odoo_tools.api.management import ManagementApi
from odoo_tools.api.db import DbApi
from odoo_tools.api.environment import Environment


@pytest.mark.skipif('TODO' not in os.environ, reason='TODO')
def test_users_list(runner):

    result = runner.invoke(
        command,
        [
            'user',
            'ls',
            'test_db'
        ]
    )

    assert result.exception is None


@pytest.mark.skipif('TODO' not in os.environ, reason='TODO')
def test_users_create(runner):
    result = runner.invoke(
        command,
        [
            'user',
            'create',
            'test_db',
            'login',
            'name'
        ]
    )

    assert result.exception is None


@pytest.mark.skipif('TODO' not in os.environ, reason='TODO')
def test_users_reset(runner):
    result = runner.invoke(
        command,
        [
            'user',
            'reset-pw',
            'test_db',
            'login'
        ]
    )

    assert result.exception is None


@pytest.mark.skipif('TODO' not in os.environ, reason='TODO')
def test_users_remove(runner):
    result = runner.invoke(
        command,
        [
            'user',
            'remove',
            'test_db',
            'login'
        ]
    )

    assert result.exception is None
