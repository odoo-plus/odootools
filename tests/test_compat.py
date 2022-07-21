import os
import pytest
from mock import patch, MagicMock
from odoo_tools.compat import SIGSEGV
from pathlib import Path

from odoo_tools.compat import (
    flush_streams,
    log,
    module_path,
    pipe,
)


def test_pipe():
    kv = {
    }

    with patch('odoo_tools.compat.subprocess') as sbp,\
         patch.dict(os.environ, kv, clear=True):

        popen = MagicMock()
        popen.returncode = 0
        sbp.Popen.return_value = popen

        ret = pipe(['odoo'])

        assert popen.wait.call_count == 1
        assert ret == 0
        assert os.environ == {}


def test_pipe_sigsegv_no_crash():
    kv = {
    }

    with patch('odoo_tools.compat.subprocess') as sbp,\
         patch.dict(os.environ, kv, clear=True):

        popen = MagicMock()
        popen.returncode = -SIGSEGV
        sbp.Popen.return_value = popen

        ret = pipe(['odoo'])

        assert popen.wait.call_count == 1
        assert ret == -SIGSEGV
        assert os.environ == {}


def test_log():
    log("message")
    log("message", 1, 2)


# def test_flush():
#     with patch('odoo_tools.compat.sys') as sis:
#         assert sis.stdout.flush.call_count == 0
#         assert sis.stderr.flush.call_count == 0
#         flush_streams()
#         assert sis.stdout.flush.call_count == 1
#         assert sis.stderr.flush.call_count == 1
#         flush_streams()
#         assert sis.stdout.flush.call_count == 2
#         assert sis.stderr.flush.call_count == 2


def test_module_path():
    with patch('odoo_tools.compat.find_spec') as fp:
        mm = MagicMock()
        mm.__bool__ = lambda self: True
        mm.origin = None
        mm.submodule_search_locations = []

        fp.return_value = mm

        with pytest.raises(ModuleNotFoundError):
            module_path('zurgbug')

        assert module_path('zurgbug', raise_not_found=False) is None


def test_module_path1():
    with patch('odoo_tools.compat.find_spec') as fp:
        mm = MagicMock()
        mm.__bool__ = lambda self: True
        mm.origin = None
        mm.submodule_search_locations = ['/a']

        fp.return_value = mm

        assert module_path('zurgbug') == Path('/a')


def test_module_path2():
    with patch('odoo_tools.compat.find_spec') as fp:
        mm = MagicMock()
        mm.__bool__ = lambda self: True
        mm.origin = Path('/a/b/__init__.py')
        mm.submodule_search_locations = ['/a']

        fp.return_value = mm

        assert module_path('zurgbug') == Path('/a/b')
