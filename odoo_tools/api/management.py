import distro
import six
import logging
import psycopg2
from contextlib import closing
from urllib.parse import urlparse

from .db import DbApi
from ..entrypoints import execute_entrypoint
from ..configuration.odoo import (
    OfficialRelease,
    GitRelease
)
from ..db import get_tables, fetch_db_version, db_filter


_logger = logging.getLogger(__name__)


class ManagementApi(object):
    def __init__(self, environment):
        self.environment = environment
        self._initialized = False

    def connection_info(self, db_or_uri):
        if db_or_uri.startswith(('postgresql://', 'postgres://')):
            # extract db from uri
            us = urlparse(db_or_uri)
            if len(us.path) > 1:
                db_name = us.path[1:]
            elif us.username:
                db_name = us.username
            else:
                db_name = us.hostname

            return {
                'dsn': db_or_uri,
                'database': db_name
            }

        connection_info = {
            'database': db_or_uri
        }

        for p in ('host', 'port', 'user', 'password', 'sslmode'):
            config_name = "db_{}".format(p)

            cfg = (
                (
                    self.options[config_name]
                    if config_name in self.options
                    else None
                ) or
                self.environment.get_config(config_name)
            )

            if cfg:
                connection_info[p] = cfg

        return connection_info

    def db_connect(self, db):
        connection_info = self.connection_info(db)
        return psycopg2.connect(**connection_info)

    def get_active_dbs(self, template=None):
        db_sql = """
        select
            db.datname
        from
            pg_database as db
            left join pg_roles as usr
                on db.datdba = usr.oid
        where
            usr.rolname = current_role and
            not db.datistemplate and
            db.datallowconn and
            db.datname not in %s
        order by
            db.datname
        """

        templates = ('postgres', template)

        with closing(self.db_connect('postgres')) as conn:
            with closing(conn.cursor()) as cr:
                cr.execute(db_sql, (templates,))

                res = [
                    name
                    for (name,) in cr.fetchall()
                ]

        return res

    def get_db_version(self, dbname):
        db_info = {
            "name": dbname
        }

        try:
            with closing(self.db_connect(dbname)) as conn:
                try:
                    with closing(conn.cursor()) as cr:
                        if len(get_tables(cr, {'ir_module_module'})) >= 1:
                            db_info['version'] = fetch_db_version(cr)
                            db_info['status'] = 'ok'
                        else:
                            db_info['status'] = 'invalid'
                except Exception:
                    db_info['status'] = 'invalid'
        except Exception:
            db_info['status'] = 'missing'

        return db_info

    def db_list(
        self,
        hostname=None,
        db_name=None,
        dbfilter=None,
        filter_missing=False,
        filter_version=False,
        filter_invalid=False,
        include_extra_dbs=False,
    ):
        if not dbfilter:
            dbfilter = self.environment.get_config('dbfilter')

        if not db_name:
            db_name = self.environment.get_config('db_name')

        db_template = self.environment.get_config('db_template') or 'template0'
        db_names = []

        if db_name:
            for db in db_name.split(','):
                temp_name = db.strip()
                if temp_name:
                    db_names.append(temp_name)

        active_dbs = self.get_active_dbs(
            template=db_template
        )

        valid_dbs = [
            self.get_db_version(dbname)
            for dbname in active_dbs
        ]

        if filter_invalid:
            valid_dbs = [
                db
                for db in valid_dbs
                if db['status'] != 'invalid'
            ]

        if filter_missing:
            valid_dbs = [
                db
                for db in valid_dbs
                if db['status'] == 'ok'
            ]

        if filter_version:
            valid_dbs = [
                db
                for db in valid_dbs
                if 'version' in db and db['version'] == filter_version
            ]

        if dbfilter:
            valid_dbs = db_filter(valid_dbs, dbfilter, hostname)

        dbs_hash = {
            db['name']: db
            for db in valid_dbs
        }

        result_dbs = []

        if db_names:
            for db in db_names:
                if db in dbs_hash:
                    result_dbs.append(dbs_hash[db])

            if include_extra_dbs:
                for db in dbs_hash.values():
                    if db['name'] not in db_names:
                        result_dbs.append(db)
        else:
            for db in dbs_hash.values():
                result_dbs.append(db)

        return result_dbs

    def db(self, database):
        """
        Returns a DbApi instance.

        Args:
            database (str): The database name

        Returns:
            DbApi: The db api object to manage odoo with the
                provided database name.
        """
        return DbApi(
            self,
            database
        )

    @property
    def config(self):
        return self.environment.odoo_config()

    @property
    def options(self):
        """
        Returns and odoo configparser.

        This method is a simple shortcut around the odoo config.
        In case odoo isn't installed, it will simply raise an
        exception that can be handled instead of having to
        handle in your code to handle if odoo can be imported.

        Raises:
            SystemError: If odoo cannot be imported.

        Returns:
            configparser: the original odoo config object.
        """
        return self.environment.odoo_options()['options']

    def initialize_odoo(self):
        """
        Initialize the odoo environment.

        This method will load entrypoints that can be declared in python
        packages or by explicitly creating them using the entrypoints
        utilities in odoo-tools.

        The first entrypoint to be called is:
        `odoo_tools.manage.before_config`. This entrypoint is supposed
        to be used to prepare the odoo configuration by filling things
        like addons paths etc. Then the entrypoint
        `odoo_tools.manage.initialize_odoo` is called. This one is responsible
        for loading the rest of odoo, for example it would setup the AddonsHook
        to load `odoo.addons` modules. Or to initialize the odoo logger. Then
        the `odoo_tools.manage.after_config` would be called to load antyhing
        that you'd want after the odoo internal configuration is effectly
        loaded.

        By default the entrypoints are undefined, this way you can
        adjust the way you want to have odoo loaded before starting
        http workers for example.
        """
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
        """
        Install odoo in the current python environment.

        Unfortunately, odoo doesn't provide a standard way to setup odoo
        through pip using pypi repositories. As a result, many companies end
        up installing odoo in many different ways. Some ways are better than
        others, but most of those methods can't be considered best practices.

        Implementing odoo's installation within this library is better in some
        ways as other methods available.

        In short, it can currently install odoo from 2 types of sources.

        Release Mode

        The release it the release
        name used in `Nightly builds <NIGHTLY>`_ of Odoo. It uses the format
        of the date of the build that you need.

        Git Mode

        The git mode will take a reference and a repository that needs to be
        fetched. The repository defaults to the odoo repository, but an
        alternative repository can be used if necessary.

        Regardless of the mode, each mode can have their file cached in an
        alternate folder. So you can try to cache the fetch in a CI environment
        to speed up odoo installation. When odoo is installed, it will pre
        process the odoo environment to provide a consistant setup. By default,
        odoo will only install addons located in odoo/addons. But in the git
        repository, addons are located in /addons and /odoo/addons. If you want
        to install odoo with pip manually, you'd have to move all addons in the
        root to the odoo/addons folder. This library does that for you.

        It's also possible to strip language translations out of the source
        folder for odoo. Most people really don't need to keep all translation
        files in their environment. It's not a big issue, but it can make
        docker images drastically smaller when translations aren't installed
        with odoo.

        This can save a non negligable amount of storage and time to upload
        large images.

        Then the source code used to install odoo gets automatically cleaned
        up to save even more space as .git data aren't necessary in a
        statically built environment. Ironically, installing odoo from scratch
        without cache can be a lot faster than loading the whole repository in
        a cache then doing incremental fetch to keep the source up to date.

        .. _NIGHTLY: https://nightly.odoo.com/
        """
        cache = opts.cache

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
        """
        It will lookup all the native packages that needs to be installed.

        Any file matching the name apt-packages.txt will be merge together
        to form the list of packages that needs to be installed.

        For example, if you have a module that requires git to be installed.
        You'd create a file with the following content:

        .. code-block::

            git

        Then when calling this method with properly configured addons_paths,
        it will automatically find this file merge it with other files
        and then you'll be able to use the output of this method and call
        the package manager of your choice with this list of package to
        install.

        Returns:
            list(str): list of package name.
        """
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

    def native_packages(self, distrib_override=None):
        python_packages = [
            "python3-pip",
            "python3-psycopg2",
            "python3-ldap",
            "python3-libsass",
            "python3-lxml",
            "python3-pillow",
            "python3-pypdf2",
            "python3-psutil",
            "python3-asn1crypto",
            # "python3-reportlab", Not needed package badly get installed
            # "python3-renderpm",
        ]

        base_packages = [
            "git",
            "curl",
        ]

        distrib_map = {
            "default": base_packages,
            "ubuntu": base_packages + python_packages,
            "fedora": base_packages + python_packages,
            "debian": base_packages + python_packages
        }

        if distrib_override is not None:
            distrib_id = distro.id()
        else:
            distrib_id = distrib_override

        if distrib_id in distrib_map:
            return distrib_map[distrib_id]
        else:
            return distrib_map['default']
