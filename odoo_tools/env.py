"""
Environment Variables
=====================
"""
from os import environ
from pathlib import Path
from .utils import obj_set, to_csv, from_bool, to_bool


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
                if self.deserializer:
                    value = self.deserializer(value)
                break
            except KeyError:
                pass
        else:
            if callable(self.default):
                value = self.default()
            else:
                value = self.default

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


class StoredSetEnv(StoredEnv):
    serializer = to_csv(',')

    def __init__(self, item_type=None, **kwargs):
        kwargs['serializer'] = StoredSetEnv.serializer
        kwargs['deserializer'] = obj_set(',', set, item_type)
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
    """

    __fields__ = set()
    ":Set<str>: Set of fields added to the class"

    # The base path where odoo is installed
    ODOO_BASE_PATH = StoredEnv()
    ":str: The base path where odoo is installed"

    ODOO_RC = StoredEnv()
    ":str: Location of the odoo.cfg file"

    ODOO_STRICT_MODE = StoredBoolEnv(default=True)
    """
    :bool: Run odoo in Strict Mode (Default: True)
    """

    ODOO_EXCLUDED_PATHS = StoredSetEnv(item_type=Path)
    """
    :Set<Path>: Excluded paths will not be looked into when
    searching modules.

    Items are defined as csv values in environment variables.
    """

    ODOO_EXTRA_PATHS = StoredSetEnv(item_type=Path)
    """
    :Set<Path>: Extra paths are paths to look for modules other
    than the default ones.

    Items are defined as csv values in environment variables.
    """

    ODOO_EXTRA_APT_PACKAGES = StoredSetEnv(
        item_type=str,
        alternate_names=['EXTRA_APT_PACKAGES']
    )
    """
    :Set<Str> Extra apt packages to install other than the one
    introspected in modules.

    Items are defined as csv values in environment variables.
    """

    ODOO_DISABLED_MODULES = StoredSetEnv(item_type=str)
    """
    :Set<str>: Odoo modules that shouldn't exist. Those would get
    removed from the addons paths.

    Items are defined as csv values in environment variables.
    """

    MASTER_PASSWORD = StoredEnv()
    """
    :str: Master password that should be set instead of the default
    one being automatically generated randomly.
    """

    SHOW_MASTER_PASSWORD = StoredEnv()
    ":bool: Log the master password in the logs."

    SKIP_PIP = StoredBoolEnv(default=False)
    """
    :bool: Skip the installation of pip modules. (Default: False)
    """

    SKIP_SUDO_ENTRYPOINT = StoredBoolEnv(default=False)
    """
    :bool: Skip the sudo entrypoint. The entry point is used
    mainly to setup things that require higher access like installing apt
    packages. (Default: False)
    """

    SKIP_POSTGRES_WAIT = StoredBoolEnv(default=False)
    """
    :bool: Tells to skip waiting for postgress to be up and running
    (Default: False)
    """

    ALLOW_DANGEROUS_SETTINGS = StoredBoolEnv(
        alternate_names=[
            'I_KNOW_WHAT_IM_DOING',
        ],
        default=False
    )
    """
    :bool: This environment variables allows it to set the
    PGPASSWORD in the environment variables. Otherwise, the entrypoint
    will fail to let odoo starts unless you specify this environment
    variable as TRUE.  The reason behind that is that it's generally not
    a good idea to set credentials in environment variables. Those values
    can be leaked easily in logs from the environment running the container
    or even in logs displaying environment variables anywhere. This
    should only be used in dev environment or test environment in which
    credentials are not that important.
    """

    DEPLOYMENT_AREA = StoredEnv()
    """
    :str: Deployment Area is just an environment variable that can
    be set to determine if it's a production environment or test
    environment.
    """

    ODOO_VERSION = StoredEnv()
    ":str: The odoo version being currently used."

    RESET_ACCESS_RIGHTS = StoredBoolEnv(default=False)
    """
    :bool: Reset access rights ensure that files in the home
    directory of the odoo user is set to the right user. This shouldn't
    be necessary in most cases. (Default: False)
    """

    APT_INSTALL_RECOMMENDS = StoredBoolEnv(default=False)
    """
    :bool: Define if you want the sudo_entrypoint to call
    apt-get with --no-install-recommends. By default, the entrypoint will
    use --no-install-recommends, but if this environment variable is set
    to TRUE. It will not add this parameter to apt-get install.
    (Default: False)
    """

    ODOO_REQUIREMENTS_FILE = StoredEnv()
    """
    :str: The path in which requirements get stored during installation of pip
    packages required by odoo addons.
    """

    USE_ODOO_LOGGER = StoredBoolEnv(default=False)
    """
    :str: Tell the app to initialize the odoo logger instead of using the
    default one. (Default: False)
    """

    PACKAGE_MAP_FILE = StoredEnv()
    """
    :str: File storing a map of :code:`{module_name: module_renamed}` to
    rename modules that shouldn't be used as is.
    """

    REQUIREMENTS_FILE_PATH = StoredEnv()
    """
    :str: Path of the requirement file to be saved. (Default: None)
    """

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
