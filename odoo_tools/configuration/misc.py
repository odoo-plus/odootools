import sys
import logging
from odoo_tools.compat import Path
import os
from contextlib import contextmanager
from six import ensure_str
from subprocess import run as sp_run, PIPE
from tempfile import TemporaryDirectory

_logger = logging.getLogger(__name__)


def find_in_path(binary, paths=None):
    """
    Find file in path

    Returns an absolute path to paths
    if the file is directly relative to '.' and
    if the file is present in paths.

    Otherwise the original path is returned.
    """
    binary_name = Path(binary)

    if binary_name.is_absolute():
        return binary

    if binary_name.parent.name != '':
        return binary

    for path in paths:
        found_binary = path / binary_name

        if found_binary.exists():
            return ensure_str(str(found_binary))

    return binary


def filter_args(args):
    """
    Take the first argument of the first args
    and filter the command line to modify the path if needed.
    """
    args = list(args)
    cmd, r_args = args[0], args[1:]
    program, options = cmd[0], cmd[1:]
    program = find_in_path(
        program,
        paths=[Path(sys.executable).parent]
    )
    cmd = [program] + options
    args = [cmd] + r_args

    return args


def run(*args, **kwargs):
    args = filter_args(args)

    if 'check' not in kwargs:
        kwargs['check'] = True

    ret = sp_run(*args, **kwargs)

    if kwargs.get('stdout') == PIPE:
        return ret.stdout

    return ret


@contextmanager
def cd(directory):
    cwd = Path.cwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(str(cwd))


def get_module_path(module):
    module_obj = sys.modules[module]
    return Path(module_obj.__file__).parent


def get_resource(module, path):
    module_path = get_module_path(module)
    return module_path / path


class DictObject(dict):
    def __getattr__(self, key):
        return self.get(key, False)

    def __setattr__(self, key, value):
        self[key] = value


def setup_logger():
    root_logger = logging.getLogger()
    log_level = os.environ.get('PYTHON_LOG', 'ERROR')
    root_logger.setLevel(log_level)
