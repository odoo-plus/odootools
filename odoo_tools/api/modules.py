import tempfile
from collections import defaultdict
from ..compat import Path
from ..modules.search import find_modules_paths
from ..utilities.requirements import merge_requirements


class ModuleApi(object):
    def __init__(self, environment):
        self.environment = environment
        self._all_manifests = None
        self._manifest_by_name = None

    def list(self, reload=False, filters=None):
        if filters is None:
            filters = set(['installable'])

        if not self._all_manifests or reload:
            all_manifests = find_modules_paths(
                self.environment.addons_paths(),
                filters,
                self.environment.context
            )
            self._all_manifests = all_manifests

        return self._all_manifests

    def get(self, name):
        if not self._manifest_by_name:
            self._manifest_by_name = defaultdict(list)
            for module in self.list():
                self._manifest_by_name[module.technical_name].append(module)

        mods = self._manifest_by_name[name]

        return mods[0]

    def server_wide_modules(self):
        """
        Search in the modules available in the environment for modules
        that are marked with the non standard property ``server_wide``.

        If a manifest is found with ``server_wide`` set to True. It will
        be returned as a server wide module.

        By default, it will always return the module ``base`` and ``web``
        as server wide modules.

        Example of use:

        .. code:: python

            with env.config():
                env.set_config(
                    'server_wide_modules',
                    ",".join(env.server_wide_modules())
                )

        Returns:
            modules (List<str>): List of server wide module names.

        """
        base_server_wide_modules = ['base', 'web']

        custom_server_wide_modules = [
            manifest.technical_name
            for manifest in self.list()
            if manifest.server_wide
        ]

        return base_server_wide_modules + custom_server_wide_modules

    def disabled_modules(self):
        """
        Generator returning a list of disabled modules based on the
        ODOO_DISABLED_MODULES environment variable.

        Example:

        .. code:: python

            for manifest in env.disabled_modules():
                manifest.remove()

        Returns:
            modules (List<Manifest>): A list of Manifest object that
                represent the found modules.
        """

        if not self.environment.context.disabled_modules:
            return

        all_modules = self.list()
        for module in all_modules:
            if module.name in self.environment.context.disabled_modules:
                yield module

    def remove_disabled(self):
        for module in self.disabled_modules():
            module.remove()

    def requirements(
        self,
        lookup_requirements=False,
        package_map=None,
        extra_paths=None,
        extra_rules=None
    ):
        if package_map is None:
            package_map = {}

        if extra_paths is None:
            extra_paths = set()

        if extra_rules is None:
            extra_rules = set()

        filters = set(['installable', 'python_dependencies'])
        modules = self.list(filters=filters)

        packages = set()
        for module in modules:
            packages |= module.requirements(package_map=package_map)

        if extra_rules or packages:
            name_template = "{}.txt"
            temp_file_count = 0

            with tempfile.TemporaryDirectory() as tempdir:
                folder_root = Path(tempdir)

                for rule in set(extra_rules) | packages:
                    file_name = name_template.format(temp_file_count)
                    file_handle = folder_root / file_name

                    with file_handle.open("wb") as temp:
                        temp.write(rule.encode('utf-8'))

                    extra_paths.add(str(file_handle))

                    temp_file_count += 1

                requirements = merge_requirements(extra_paths)
        else:
            requirements = merge_requirements(extra_paths)

        return set(requirements)
