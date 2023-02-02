"""
Compatibility
=============

This module provides a common interface for functions that have
incompatibilities between python versions. This is an internal
module and you shouldn't import things here in your project as
they may be subject to change or disapear without notice.

.. note::
    This module is deprecated and will be refactored. Initially, its
    purpose was to provide a common interface for some libraries that
    had different interfaces between python2 and python3. As of now,
    odoo-tools doesn't attempt to work on python2 anymore.


"""
import sys
import signal
import shlex
# import re
import os
import subprocess
from pathlib import Path
# from configparser import ConfigParser, NoOptionError, NoSectionError
from importlib.util import find_spec
import logging

_logger = logging.getLogger(__name__)

SIGSEGV = signal.SIGSEGV.value
quote = shlex.quote


def module_path(module, raise_not_found=True):
    """
    A function that returns the path in which the module is located.

    Parameters:
        module (str): The name of the module to check.

    Returns:
        path (Path): the path of the module.
    """
    spec = find_spec(module)

    if not spec:
        if raise_not_found:
            raise ModuleNotFoundError(
                "Module {} cannot be found".format(module)
            )
        else:
            return None

    if spec.origin:
        return Path(spec.origin).parent
    else:
        for path in spec.submodule_search_locations:
            return Path(path)
        else:
            if raise_not_found:
                raise ModuleNotFoundError(
                    "Module {} cannot be found".format(module)
                )
            else:
                return None


def pipe(args):
    """
    Call the process with std(in,out,err)

    Parameters:
        args (List<str>): A list of parameters to be passed to Popen.

    Returns:
        returncode (int): The returncode of the program
    """
    _logger.info("Executing external command %s" % " ".join(args))

    env = os.environ.copy()
    env['DEBIAN_FRONTEND'] = 'noninteractive'

    process = subprocess.Popen(
        args,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=env
    )

    process.wait()

    _logger.info(
        (
            "External command execution completed with returncode(%s)"
        ) % process.returncode
    )

    if process.returncode == -SIGSEGV:
        _logger.info("PIPE call segfaulted")
        _logger.info("Failed to execute %s" % args)

    return process.returncode
