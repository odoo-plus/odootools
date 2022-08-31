import os
import toml
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from configparser import NoSectionError, NoOptionError

from ..exceptions import OdooNotInstalled
from ..compat import module_path
from ..modules.search import find_addons_paths
from ..utils import (
    filter_excluded_paths,
    to_path_list,
    convert_env_value,
    ConfigParser
)
from ..utilities.config import get_env_params, parse_value, get_defaults
from ..utilities.loaders import FileLoader
from ..configuration.misc import (
    get_resource
)

from .context import Context
from .management import ManagementApi
from .modules import ModuleApi
from .services import ServiceApi


_logger = logging.getLogger(__name__)


class Environment(object):
    """
    Odoo Environment object.

    The odoo environment object is a container that store all
    the information required to prepare an environment for odoo.

    It can be used to browse the available modules in the configured
    odoo environment.

    Or to setup environment variables for the running odoo instance.

    It can also be used to configure the odoo.cfg file based on the
    current environment.

    Attributes:
        context (Context): The context to use

        env (Environment): The environment variables container


        requirement_file_path (Path): The path where to store the requirements
            file when merging pip requirements.

    """

    def __init__(
        self,
        context=None,
    ):
        """
        Initialize an environment.

        Parameters:
            context (Context): The context to use.
            env (Environment): The environment to use.
            strict_mode (bool): If the environment is strict.
        """
        if context is None:
            context = Context.from_env()

        self.context = context
        self.modules = ModuleApi(self)
        self.manage = ManagementApi(self)
        self.services = ServiceApi(self)

        self._config = ConfigParser()
        self._nested = False
        self._read_config = False
        self.loader = FileLoader()

        self._prepare_parser()

    def _prepare_parser(self):
        self.loader.parsers['.toml'] = lambda data: toml.loads(data)
        self.loader.parsers['.json'] = lambda data: json.loads(data)

    def path(self):
        """
        Returns the path where odoo is installed and can be imported.

        The base addons are installed in the folder `addons` relative
        to this path.
        """
        if self.context.odoo_base_path:
            return Path(self.context.odoo_base_path)

        try:
            path = module_path("odoo")
        except Exception:
            try:
                path = module_path("openerp")
            except Exception:
                raise OdooNotInstalled("Cannot find odoo base path")

        return path

    def check_odoo(self):
        try:
            self.path()
        except Exception:
            raise OdooNotInstalled(
                "Cannot use this api without odoo being installed"
            )

    def set_config(self, key, value, section='options'):
        """
        Set a configuration settings in the currently open configuration file.

        Example:

        .. code:: python

            env.set_config('server_wide_modules', 'web,base')
            env.set_config('max_handlers', '3', 'custom_section')

        Parameters:

            key (str): The name of the config to set.

            value (str): The value to store in the config

            section (str): The section to use in the ConfigParser object. By
                default, it uses the ``'options'`` section. This is the default
                section used by odoo. But the section can be set to something
                different to define additional sections for use.
        """
        with self.config():
            self._config.set(section, key, value)

    def get_config(self, key, section='options'):
        """
        Get a configuration settings in the currently open configuration file.
        """
        try:
            with self.config(readonly=True):
                return parse_value(self._config.get(section, key))
        except NoOptionError:
            return None
        except NoSectionError:
            return None

    @contextmanager
    def config(self, readonly=False):
        """
        A context manager that can be used to read/write configuration for
        odoo.

        The context manager saves the configuration file when it is closed.


        .. code:: python

            with env.config():
                env.set_config('server_wide_modules', 'web,base')

        """
        config_path = Path(self.context.odoo_rc)

        nested = self._nested
        is_top = False

        if not nested:
            self._nested = True
            is_top = True

        if not nested and config_path.exists() and not self._read_config:
            try:
                self._read_config = True
                self._config.read(str(config_path))
            except Exception:
                _logger.info("Couldn't read ODOO_RC file.", exc_info=True)

        if not self._config._defaults and self.odoo_version():
            try:
                params_by_name = get_env_params(self, self.odoo_version())
            except OdooNotInstalled:
                params_by_name = {}

            self._config._defaults = get_defaults(params_by_name)

        try:
            yield self._config
        except Exception:
            raise
        finally:
            if is_top:
                self._nested = False

        if not nested and not readonly:
            try:
                with config_path.open('w') as out:
                    defaults = self._config._defaults
                    self._config._defaults = {}
                    self._config.write(out)
                    self._config._defaults = defaults
            except Exception:
                _logger.error("Couldn't write config ", exc_info=True)

    def addons_paths(self):
        """
        Returns the addons path configured for this environment.

        For example, it would find the path addons in the odoo installed
        folder. And in custom paths defined to search for addons.

        If an addons path had modules in ``/a/b``, ``/a/d/e/f`` and ``/a/b/c``.
        It would return the following list of addons paths.

        .. code:: python

            ['/a/b', '/a/b/c', '/a/d/e/f']

        Odoo doesn't load folders recursively so if you have modules within
        folder that also contains modules. The addons_paths have to be defined.

        With this, you can store your modules in to ``'/addons'`` and only
        define as custom_paths ``'/addons'``. If there are modules in
        ``'/addons/**'``.  Those will be returned by ``addons_paths()``.


        .. code:: python

            addons_paths = ",".join(env.addons_paths())

            with env.config():
                env.set_config("addons_path", addons_paths)

        Returns:
            paths (List<Path>): The list of paths containing installable
                addons.
        """
        try:
            with self.config(readonly=True) as config:
                paths = config.get('options', 'addons_path')

            config_paths = set(
                Path(path)
                for path in paths.split(',')
                if path
            )

            if len(config_paths) > 0 and not self.context.force_addons_lookup:
                return config_paths

        except Exception:
            config_paths = set()

        base_addons_paths = config_paths

        try:
            base_addons = self.path() / "addons"
            if not self.context.exclude_odoo:
                base_addons_paths.add(base_addons)
            else:
                self.context.excluded_paths.add(base_addons)
        except OdooNotInstalled:
            pass

        base_addons_paths |= self.context.custom_paths

        orig_valid_paths = find_addons_paths(
            base_addons_paths,
            options=self.context
        )

        if self.context.excluded_paths:
            excluded_paths = to_path_list(self.context.excluded_paths)
            valid_paths = filter_excluded_paths(
                orig_valid_paths, excluded_paths
            )
        else:
            valid_paths = orig_valid_paths

        return valid_paths

    def odoo_config(self):
        """
        Returns odoo config regardless of being in openerp/odoo
        """
        try:
            from odoo.tools import config as odoo_config
            return odoo_config
        except ImportError:
            try:
                from openerp.tools import config as odoo_config
                return odoo_config
            except (ImportError, ModuleNotFoundError):
                raise OdooNotInstalled(
                    "Cannot use config without odoo being installed"
                )

    def odoo_options(self):
        env_options = self.env_options()

        options = {}

        with self.config(readonly=True) as config:
            for section, values in config._sections.items():
                sections_vals = options.setdefault(section, {})
                for key, value in values.items():
                    sections_vals[key] = value

        if 'options' in options:
            options['options'].update(env_options)
        else:
            options['options'] = env_options

        return options

    def env_options(self):
        """
        Load environment variable options.
        """
        try:
            params_by_name = get_env_params(self, self.odoo_version())
        except OdooNotInstalled:
            params_by_name = {}

        configs = {}

        for key, value in os.environ.items():
            if key in params_by_name:
                option = params_by_name[key]
                config_name = option[0]
                converted_value = convert_env_value(key, value)
                configs[config_name] = converted_value

        return configs

    def sync_options(self):
        """
        Sync options to odoo configmanager

        Loads the config file and loads the environment
        variables options. Then set the options into
        `odoo.tools.config` in the options and misc
        parameters.
        """
        config = self.odoo_config()
        odoo_options = self.odoo_options()

        opts = odoo_options.pop('options')

        config.options.update(opts)

        for section, values in odoo_options.items():
            sec = config.misc.setdefault(section, {})
            for key, value in values.items():
                sec[key] = parse_value(value)

    def requirement_files(self, lookup_requirements=False):
        found_files = set()

        for cur_path in self.addons_paths():
            if lookup_requirements:
                found_files |= set(cur_path.glob("**/requirements.txt"))
            else:
                requirement_file = cur_path / 'requirements.txt'
                if requirement_file.exists():
                    found_files.add(requirement_file)

        return found_files

    def _default_package_map(self):
        version = self.odoo_version()

        if not version:
            return {}

        file_path = "packages/map-{version}.toml".format(
            version=version
        )

        resource_path = get_resource('odoo_tools', file_path)

        if not resource_path.exists():
            return {}

        with resource_path.open('r') as fin:
            data = toml.load(fin)

        return data

    def package_map(self):
        """
        Returns a package map.

        The package map is used to map some module name
        to python package names.

        By default, in newer versions of odoo, it will check
        for the package name. But unfortunately some modules
        will still have the module name defined in their
        python external dependencies.

        When requirements are built from the odoo modules available
        in the odoo environment. It will wrongly attempt to install
        let say the module "ldap". ldap is the name of the module
        that can be imported, but the package that needs to be
        installed is python-ldap.

        Such map could look like this:

        .. code-block:: python

            {'ldap': 'python-ldap'}

        Then when the packages required are found, they can be mapped
        to those package names to find the exact python package name.

        Mapping a name to an empty string would remove the name from
        the requirements. This can be useful to remove package defined
        in the external dependencies that aren't actual packages but
        builtin dependencies that would be already part of python
        itself.

        .. code-block:: python

            {'asyncio': ''}

        The behaviour could be also useful when you want to install an
        alternative to let say the barcode module.

        Returns:
            dict: Key, Value of mapped module/package name.
        """
        base_map = self._default_package_map()

        package_map_file = self.context.package_map_file
        if not package_map_file:
            return base_map

        package_map_path = Path(package_map_file)

        if not package_map_path.exists():
            return base_map

        content = package_map_path.open('r').read()
        package_map = toml.loads(content)

        new_vals = {
            key.lower(): value.lower()
            for key, value in package_map.items()
        }

        base_map.update(new_vals)
        return base_map

    def odoo_version(self):
        """
        Returns the odoo version.

        In case odoo isn't installed, it will fallback to the
        context variable `odoo_version` which can be set through
        environment variable ODOO_VERSION.

        Returns:
            int|None: The major version number or None
        """
        try:
            from odoo.release import version_info
            return version_info[0]
        except ImportError:
            try:
                return int(float(self.context.odoo_version))
            except Exception:
                return None
