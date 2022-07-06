import os
from ..compat import Path
from ..env import EnvironmentVariables


class Context(object):
    """
    The context in which you use the Environment.

    For example, the context will be able to load environment
    variables configured in the running environment.

    The environment variables are then passed to the context
    and then the application is able to have a proper behaviour
    based on the environment.

    Attributes:

        strict_mode (bool): Can be used to run in strict mode. In strict mode,
            the library doesn't ignore exceptions and raise exceptions to the
            caller.

            This is useful in CI pipelines that may want to know in case of
            failure. One example is when running Pip install modules, it may
            complete installing but should stop in case some dependencies
            can't be installed properly.

            In some cases, when running a docker image, you may want your
            docker container to keep running even if some pip dependencies
            can't be installed/upgraded.

        custom_paths (Set<Path>): A list of ``Path`` that contains modules.
            The path may not directly contain modules as this library can be
            used to find modules recursively in given paths.
    """
    def __init__(
        self,
        custom_paths=None,
        strict_mode=True,
        requirements_file_path=None,
        odoo_base_path=None,
        excluded_paths=None,
        exclude_odoo=False,
        disabled_modules=False,
        odoo_rc=False,
        include_odoo_entrypoints=True,
        force_addons_lookup=False,
        init_logger=True,
        run_only=False,
        extra_apt_packages=None,
        apt_install_recommends=False,
        package_map_file=None,
        skip_pip=False,
        skip_sudo_entrypoint=False,
        skip_postgres_wait=False,
        allow_dangerous_settings=False,
        odoo_version=None,
        master_password=None,
        show_master_password=True,
        reset_access_rights=False,
        requirement_file_path=None,
    ):
        if custom_paths is None:
            custom_paths = set()

        if not excluded_paths:
            excluded_paths = set()

        if extra_apt_packages is None:
            extra_apt_packages = set()

        self.custom_paths = custom_paths
        self.requirements_file_path = requirements_file_path
        self.odoo_base_path = odoo_base_path
        self.excluded_paths = excluded_paths
        self.exclude_odoo = exclude_odoo
        self.disabled_modules = disabled_modules
        self.odoo_rc = odoo_rc or self.default_odoorc()
        self.include_odoo_entrypoints = include_odoo_entrypoints
        self.force_addons_lookup = force_addons_lookup
        self.init_logger = init_logger
        self.run_only = run_only
        self.extra_apt_packages = extra_apt_packages
        self.apt_install_recommends = apt_install_recommends
        self.package_map_file = package_map_file
        self.skip_pip = skip_pip
        self.skip_sudo_entrypoint = skip_sudo_entrypoint
        self.skip_postgres_wait = skip_postgres_wait
        self.allow_dangerous_settings = allow_dangerous_settings
        self.odoo_version = odoo_version
        self.master_password = master_password
        self.show_master_password = show_master_password
        self.strict_mode = strict_mode
        self.reset_access_rights = reset_access_rights
        self.requirement_file_path = requirement_file_path

    def default_odoorc(self):
        directories = [
            Path.cwd(),
        ]

        if 'HOME' in os.environ:
            path = Path(os.environ['HOME'])
            if path not in directories:
                directories.append(path)

        var_lib_path = Path("/var/lib/odoo")
        if var_lib_path not in directories:
            directories.append(var_lib_path)

        filenames = [
            '.odoorc',
            '.openerp_serverrc',
            'odoo.cfg'
        ]

        for directory in directories:
            for filename in filenames:
                rc_file = directory / filename
                if rc_file.exists():
                    return rc_file
        else:
            return Path.cwd() / 'odoo.cfg'

    @classmethod
    def from_env(klass, envvars=None):
        """
        Creates a ``Context`` from environment variables.
        """
        if envvars is None:
            envvars = EnvironmentVariables()

        args = {
            "custom_paths": set()
        }

        if envvars.ODOO_EXTRA_PATHS:
            args['custom_paths'] |= {
                Path(path)
                for path in envvars.ODOO_EXTRA_PATHS
            }

        if envvars.ODOO_STRICT_MODE is not None:
            args['strict_mode'] = envvars.ODOO_STRICT_MODE

        if envvars.ODOO_REQUIREMENTS_FILE:
            args['requirements_file_path'] = Path(
                envvars.ODOO_REQUIREMENTS_FILE
            )
        else:
            args['requirements_file_path'] = Path(
                '/var/lib/odoo/requirements.txt'
            )

        if envvars.ODOO_BASE_PATH:
            args['odoo_base_path'] = envvars.ODOO_BASE_PATH

        if envvars.ODOO_EXCLUDED_PATHS:
            args['excluded_paths'] = {
                Path(path)
                for path in envvars.ODOO_EXCLUDED_PATHS
            }

        if envvars.ODOO_DISABLED_MODULES:
            args['disabled_modules'] = envvars.ODOO_DISABLED_MODULES

        if envvars.ODOO_RC:
            args['odoo_rc'] = Path(envvars.ODOO_RC)

        args['init_logger'] = envvars.USE_ODOO_LOGGER

        args['extra_apt_packages'] = envvars.ODOO_EXTRA_APT_PACKAGES
        args['apt_install_recommends'] = envvars.APT_INSTALL_RECOMMENDS
        args['package_map_file'] = envvars.PACKAGE_MAP_FILE

        # Entrypoint
        args['skip_sudo_entrypoint'] = envvars.SKIP_SUDO_ENTRYPOINT
        args['skip_pip'] = envvars.SKIP_PIP
        args['skip_postgres_wait'] = envvars.SKIP_POSTGRES_WAIT
        args['allow_dangerous_settings'] = envvars.ALLOW_DANGEROUS_SETTINGS
        args['odoo_version'] = envvars.ODOO_VERSION
        args['master_password'] = envvars.MASTER_PASSWORD
        args['show_master_password'] = envvars.SHOW_MASTER_PASSWORD
        args['reset_access_rights'] = envvars.RESET_ACCESS_RIGHTS
        args['requirement_file_path'] = (
            Path(envvars.REQUIREMENTS_FILE_PATH)
            if envvars.REQUIREMENTS_FILE_PATH
            else None
        )

        return Context(**args)
