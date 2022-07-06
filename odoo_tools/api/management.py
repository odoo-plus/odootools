import six
import logging

from .db import DbApi
from ..entrypoints import execute_entrypoint
from ..configuration.odoo import (
    OfficialRelease,
    GitRelease
)


_logger = logging.getLogger(__name__)


class MangementApi(object):
    def __init__(self, environment):
        self.environment = environment
        self._initialized = False

    def db(self, database):
        return DbApi(
            self,
            database
        )

    @property
    def config(self):
        try:
            from odoo.tools import config
            return config
        except Exception:
            pass

        raise SystemError("Odoo doesn't seems to be installed")

    def initialize_odoo(self):
        self._initialized = True
        execute_entrypoint("odoo_tools.manage.before_config", self)
        execute_entrypoint("odoo_tools.manage.initialize_odoo", self)
        execute_entrypoint("odoo_tools.manage.after_config", self)

    def install_odoo(
        self,
        version,
        release=None,
        ref=None,
        repo='https://github.com/odoo/odoo.git',
        opts=None
    ):
        if hasattr(opts, 'cache'):
            cache = opts.cache
        else:
            cache = None

        if release:
            installer = OfficialRelease(
                version,
                release,
                options=opts,
                cache=cache
            )
        else:
            installer = GitRelease(
                version,
                repo,
                ref or version,
                options=opts,
                cache=cache
            )

        with installer:
            if installer.need_update():
                installer.fetch()
                installer.checkout()
                installer.install()

    def packages(self):
        package_list = set()
        paths = self.environment.addons_paths()

        _logger.info(
            "Looking up for packages in %s",
            paths
        )

        for addons_path in paths:
            for packages in addons_path.glob('**/apt-packages.txt'):
                _logger.info("Installing packages from %s", packages)

                with packages.open('r') as pack_file:
                    lines = [
                        six.ensure_text(line).strip()
                        for line in pack_file
                        if six.ensure_text(line).strip()
                    ]

                    package_list.update(set(lines))

        context = self.environment.context

        _logger.info(
            "Adding extra packages %s",
            context.extra_apt_packages
        )

        for package in context.extra_apt_packages:
            package_list.add(
                six.ensure_text(package).strip()
            )

        return package_list
