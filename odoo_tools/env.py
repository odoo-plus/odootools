"""
Environment Variables
=====================
"""
from os import environ
from .utils import from_csv


class EnvironmentVariables(object):
    """
    EnvironmentVariables parser

    Attributes:
        ODOO_BASE_PATH: The base path where odoo is installed

        ODOO_RC: Location of the odoo.cfg file

        ODOO_STRICT_MODE: Run odoo in Strict Mode

        ODOO_EXCLUDED_PATHS (list): Excluded paths will not be looked into when
            searching modules

        ODOO_EXTRA_PATHS (list): Extra paths are paths to look for modules other
            than the default ones.

        ODOO_EXTRA_APT_PACKAGES: Extra apt packages to install other than the one
            introspected in modules.

        ODOO_DISABLED_MODULES: Odoo modules that shouldn't exist. Those would get
            removed from the addons paths.

        MASTER_PASSWORD: Master password that should be set instead of the default
            one being automatically generated randomly.

        SHOW_MASTER_PASSWORD: Log the master password in the logs.

        SKIP_PIP: Skip the installation of pip modules.

        SKIP_SUDO_ENTRYPOINT: Skip the sudo entrypoint. The entry point is used
            mainly to setup things that require higher access like installing apt
            packages.

        SKIP_POSTGRES_WAIT: Tells to skip waiting for postgress to be up and
            running

        I_KNOW_WHAT_IM_DOING: This environment variables allows it to set the
            PGPASSWORD in the environment variables. Otherwise, the entrypoint
            will fail to let odoo starts unless you specify this environment
            variable as TRUE.  The reason behind that is that it's generally not
            a good idea to set credentials in environment variables. Those values
            can be leaked easily in logs from the environment running the container
            or even in logs displaying environment variables anywhere. This
            should only be used in dev environment or test environment in which
            credentials are not that important.

        ODOO_VERSION: The odoo version being currently used.

        RESET_ACCESS_RIGHTS: Reset access rights ensure that files in the home
            directory of the odoo user is set to the right user. This shouldn't
            be necessary in most cases.

        DEPLOYMENT_AREA: Deployment Area is just an environment variable that can
            be set to determine if it's a production environment or test
            environment.

        APT_INSTALL_RECOMMENDS: Define if you want the sudo_entrypoint to call
            apt-get with --no-install-recommends. By default, the entrypoint will
            use --no-install-recommends, but if this environment variable is set
            to TRUE. It will not add this parameter to apt-get install.

        ODOO_REQUIREMENTS_FILE: The path in which requirements get stored during
            installation of pip packages required by odoo addons.

        USE_ODOO_LOGGER: Tell the app to initialize the odoo logger instead of
            using the default one.

        PACKAGE_MAP_FILE: File storing a map of {module_name: module_renamed} to
            rename modules that shouldn't be used as is.
    """
    def __init__(self):
        self.ODOO_BASE_PATH = environ.get('ODOO_BASE_PATH')
        self.ODOO_RC = environ.get('ODOO_RC')
        self.ODOO_STRICT_MODE = environ.get('ODOO_STRICT_MODE')
        self.ODOO_EXCLUDED_PATHS = from_csv(
            environ.get('ODOO_EXCLUDED_PATHS', ''),
            set
        )
        self.ODOO_EXTRA_PATHS = from_csv(
            environ.get('ODOO_EXTRA_PATHS'),
            set
        )
        self.ODOO_EXTRA_APT_PACKAGES = from_csv(
            environ.get('ODOO_EXTRA_APT_PACKAGES') or
            environ.get('EXTRA_APT_PACKAGES'),
            set
        )
        self.ODOO_DISABLED_MODULES = from_csv(
            environ.get('ODOO_DISABLED_MODULES'),
            set
        )

        self.MASTER_PASSWORD = environ.get('MASTER_PASSWORD')
        self.SHOW_MASTER_PASSWORD = environ.get('SHOW_MASTER_PASSWORD')

        self.SKIP_PIP = environ.get('SKIP_PIP')
        self.SKIP_SUDO_ENTRYPOINT = environ.get('SKIP_SUDO_ENTRYPOINT')
        self.SKIP_POSTGRES_WAIT = environ.get('SKIP_POSTGRES_WAIT')
        self.I_KNOW_WHAT_IM_DOING = environ.get('I_KNOW_WHAT_IM_DOING')

        self.ALLOW_DANGEROUS_SETTINGS = environ.get(
            'I_KNOW_WHAT_IM_DOING',
            environ.get(
                'ALLOW_DANGEROUS_SETTINGS',
                ''
            )
        ).lower() == 'true'

        self.DEPLOYMENT_AREA = environ.get('DEPLOYMENT_AREA')

        self.ODOO_VERSION = environ.get('ODOO_VERSION')

        self.RESET_ACCESS_RIGHTS = environ.get('RESET_ACCESS_RIGHTS', '')

        self.APT_INSTALL_RECOMMENDS = environ.get('APT_INSTALL_RECOMMENDS')

        self.ODOO_REQUIREMENTS_FILE = environ.get('ODOO_REQUIREMENTS_FILE')

        self.USE_ODOO_LOGGER = environ.get('USE_ODOO_LOGGER')

        self.PACKAGE_MAP_FILE = environ.get('PACKAGE_MAP_FILE')

        self.REQUIREMENTS_FILE_PATH = environ.get('REQUIREMENTS_FILE_PATH')
