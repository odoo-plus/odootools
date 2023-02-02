"""
Environment Variables
=====================
"""
from os import environ


def path_list(delimiter=',', container=list):

    def deserializer(value):
        from pathlib import Path

        value = value or ''
        elems = value.split(delimiter)

        value = [
            Path(path.strip())
            for path in elems
            if path.strip()
        ]

        return container(value)

    return deserializer


def to_csv(delimiter=','):

    def serializer(value):
        return delimiter.join([
            str(elem)
            for elem in value
        ])

    return serializer


def from_bool(value):
    return str(value)


def to_bool(value):
    if value:
        return value.lower() == 'true'
    else:
        return False


class EnvironmentVariable(property):
    def __init__(
        self,
        serializer=None,
        deserializer=None,
        alternate_names=None,
        default=None,
        **kwargs
    ):
        super().__init__()
        self.__name = None
        self.serializer = serializer
        self.deserializer = deserializer
        self.default = default
        self.alternate_names = alternate_names or []

    def __set_name__(self, owner, name):
        self.__name = name

    def __get__(self, owner, klass):
        for name in [self.__name] + self.alternate_names:
            try:
                value = environ[name]
                break
            except KeyError:
                pass
        else:
            if callable(self.default):
                value = self.default()
            else:
                value = self.default

        if self.deserializer:
            value = self.deserializer(value)

        return value

    def __set__(self, owner, value):
        if self.serializer:
            serialized_value = self.serializer(value)
            environ[self.__name] = serialized_value
        else:
            environ[self.__name] = value


class StoredEnv(EnvironmentVariable):
    def __init__(self, readonly=False, **kwargs):

        if readonly is not False:
            kwargs['readonly'] = readonly

        super().__init__(**kwargs)
        self.__name = None
        self.__readonly = readonly

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        owner.__fields__.add(name)
        self.__name = name

    def __get__(self, owner, klass):
        try:
            return owner._values[self.__name]
        except KeyError:
            value = super().__get__(owner, klass)
            owner._values[self.__name] = value
            return value

    def __set__(self, owner, value):
        super().__set__(owner, value)
        if not self.__readonly:
            owner._values[self.__name] = value


class StoredPathEnv(StoredEnv):
    deserializer = path_list(',', set)
    serializer = to_csv(',')

    def __init__(self, **kwargs):
        kwargs['serializer'] = StoredPathEnv.serializer
        kwargs['deserializer'] = StoredPathEnv.deserializer
        super().__init__(**kwargs)


class StoredBoolEnv(StoredEnv):
    deserializer = to_bool
    serializer = from_bool

    def __init__(self, **kwargs):
        kwargs['serializer'] = StoredBoolEnv.serializer
        kwargs['deserializer'] = StoredBoolEnv.deserializer
        super().__init__(**kwargs)


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

    """

    __fields__ = set()

    # The base path where odoo is installed
    ODOO_BASE_PATH = StoredEnv()

    ODOO_RC = StoredEnv()
    ODOO_STRICT_MODE = StoredEnv()
    ODOO_EXCLUDED_PATHS = StoredPathEnv()

    ODOO_EXTRA_PATHS = StoredPathEnv()

    ODOO_EXTRA_APT_PACKAGES = StoredPathEnv(
        alternate_names=['EXTRA_APT_PACKAGES']
    )

    ODOO_DISABLED_MODULES = StoredPathEnv()

    MASTER_PASSWORD = StoredEnv()
    SHOW_MASTER_PASSWORD = StoredEnv()

    SKIP_PIP = StoredBoolEnv(default=False)
    SKIP_SUDO_ENTRYPOINT = StoredBoolEnv(default=False)
    SKIP_POSTGRES_WAIT = StoredBoolEnv(default=False)

    ALLOW_DANGEROUS_SETTINGS = StoredBoolEnv(
        alternate_names=[
            'I_KNOW_WHAT_IM_DOING',
        ],
        default=False
    )

    DEPLOYMENT_AREA = StoredEnv()

    ODOO_VERSION = StoredEnv()

    RESET_ACCESS_RIGHTS = StoredBoolEnv(default=False)

    APT_INSTALL_RECOMMENDS = StoredBoolEnv(default=False)

    ODOO_REQUIREMENTS_FILE = StoredEnv()

    # Tell the app to initialize the odoo logger instead of using the default
    # one.
    USE_ODOO_LOGGER = StoredBoolEnv(default=False)

    # File storing a map of {module_name: module_renamed} to rename modules
    # that shouldn't be used as is.
    PACKAGE_MAP_FILE = StoredEnv()

    REQUIREMENTS_FILE_PATH = StoredEnv()

    def __init__(self):
        self._values = {}

    @classmethod
    def fields(cls):
        for attr in cls.__fields__:
            yield attr

    def values(self):
        return {
            field: getattr(self, field)
            for field in self.fields()
        }
