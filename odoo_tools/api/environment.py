import os
import toml
import sys
import logging
from pathlib import Path
from contextlib import contextmanager
from configparser import NoSectionError, NoOptionError

from ..exceptions import OdooNotInstalled, NoConfigError
from ..compat import module_path
from ..modules.search import find_addons_paths, find_modules_paths
from ..utils import (
    filter_excluded_paths,
    to_path_list,
    convert_env_value,
    ConfigParser
)
from ..configuration.misc import (
    get_resource
)

from .context import Context
from .management import MangementApi
from .modules import ModuleApi


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
        self.manage = MangementApi(self)
        self._config = None

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
        if not self._config:
            raise NoConfigError("No config file currently open")

        self._config.set(section, key, value)

    def get_config(self, key, section='options'):
        """
        Get a configuration settings in the currently open configuration file.
        """
        if not self._config:
            raise NoConfigError("No config file currently open")

        try:
            return self._config.get(section, key)
        except NoOptionError:
            return None
        except NoSectionError:
            return None

    @contextmanager
    def config(self):
        """
        A context manager that can be used to read/write configuration for
        odoo.

        The context manager saves the configuration file when it is closed.


        .. code:: python

            with env.config():
                env.set_config('server_wide_modules', 'web,base')

        """
        config_path = Path(self.context.odoo_rc)

        if not self._config:
            nested = False
            conf = ConfigParser()
        else:
            nested = True
            conf = self._config

        if not self._config and config_path.exists():
            try:
                conf.read(str(config_path))
            except Exception:
                _logger.info("Couldn't read ODOO_RC file.", exc_info=True)

        try:
            self._config = conf
            yield conf
        except Exception:
            if not nested:
                self._config = None
            raise
        finally:
            if not nested:
                self._config = None

        if not nested:
            try:
                with config_path.open('w') as out:
                    conf.write(out)
            except Exception:
                _logger.info("Couldn't write config ", exc_info=True)
                with config_path.open('wb') as out:
                    conf.write(out)

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
                env.set_config("addons_paths", addons_paths)

        Returns:
            paths (List<Path>): The list of paths containing installable
                addons.
        """
        try:
            with self.config() as config:
                paths = config.get('options', 'addons_paths')

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
            if not self.context.exclude_odoo:
                base_addons = self.path() / "addons"
                base_addons_paths.add(base_addons)
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

    def env_options(self):
        try:
            odoo_config = self.odoo_config()
        except OdooNotInstalled:
            return {}

        params_by_name = {}
        for key, opt in odoo_config.casts.items():
            value_opt = opt.get_opt_string()
            value_opt = value_opt.upper().replace('--', 'ODOO_')
            value_opt = value_opt.replace('-', '_')
            params_by_name[value_opt] = key

        configs = {}

        for key, value in os.environ.items():
            if not key.startswith('ODOO_'):
                continue

            if key in params_by_name:
                config_name = params_by_name[key]
                converted_value = convert_env_value(key, value)
                configs[config_name] = converted_value

        return configs

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
        Return the odoo version
        =======================

        In case odoo isn't installed, it will fallback to the
        context variable `odoo_version` which can be set through
        environment variable ODOO_VERSION.

        Returns:
        int: The major version number
        """
        try:
            from odoo.release import version_info
            return version_info[0]
        except ImportError:
            try:
                return int(float(self.context.odoo_version))
            except Exception:
                return None
