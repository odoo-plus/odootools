"""
Search
======

The module search regroup a series of functions used to search
modules and handle their dependencies. This collection of functions,
can be used to determine which folder contains installable modules
and it can also be used to predetermine which module would require
to be installed if a given module was installed.
"""
import logging

from odoo_tools.compat import Path, module_path
from ..api.objects import Manifest


import pkg_resources

_logger = logging.getLogger(__name__)


def filter_installable(manifest):
    """
    Filter for installable modules
    """
    return manifest.installable


def filter_noninstallable(manifest):
    """
    Filter for not installable modules.

    This is mainly the opposite of `filter_installable`.
    """
    return not filter_installable(manifest)


def filter_python_dependencies(manifest):
    """
    Filter modules with python dependencies.
    """
    if (
        manifest.external_dependencies and
        manifest.external_dependencies.get('python')
    ):
        return True
    else:
        return False


def get_filter(filter_names):
    """
    Returns a filter function with the provided filter names.

    If all filter function returns True, then the object will
    not get filtered out of the set/list.

    For example, a filter of installable, python_dependencies on
    a list of manifests will return all manifests that are
    installable and that have python dependencies.

    Args:
        filter_names (Set(str)): Set of filter names.

    Returns:
        Boolean: if the manifest validates the current set of
            filters.
    """
    if not filter_names:
        return lambda module: True

    filters = []

    if 'installable' in filter_names:
        filters.append(filter_installable)

    if 'non_installable' in filter_names:
        filters.append(filter_noninstallable)

    if 'python_dependencies' in filter_names:
        filters.append(filter_python_dependencies)

    def filter_module(manifest):
        return all([check(manifest) for check in filters])

    return filter_module


def fast_search_manifests(path):
    """
    Quickly search into directoy for manifest files.

    In order to speed up the search recursively, it
    will stop search in folders that have one of the
    possible manifest name.

    It doesn't loop through all files in the directory.
    Instead it checks for manifest files then if none
    are found, it will lookup for folders to look into.

    All other files are skipped. Then the cycle repeats,
    until it finds a manifest or there are no more folders
    to search into.

    Args:
        path (Path): Path in which the manifest lookup occurs.

    Returns:
        list(Path): List of manifests paths.
    """
    filenames = ['__manifest__.py', '__openerp__.py']
    found_paths = []
    blacklist = ['setup', '.git']

    for manifest in filenames:
        manifest_path = path / manifest
        if manifest_path.exists():
            return [manifest_path]

    dirs_to_search = []
    if path.exists():
        for cpath in path.iterdir():
            if cpath.name in blacklist:
                continue
            if cpath.is_dir():
                dirs_to_search.append(cpath)
                continue
            # Never used because tested before looking up into dir
            # if cpath.name in filenames:
            #     found_paths.append(cpath)
            #     return
        else:
            for cpath in dirs_to_search:
                found_paths += fast_search_manifests(cpath)

    return found_paths


def find_modules(path, filters=None):
    """
    Search for manifests recursively in a specified folder.

    Each Path is then converted to a Manifest object.

    Args:
        path (Path): Path in which the manifest lookup occurs.

        filters (Set(str)): Set of filters to ignore some manifests.

    Returns:
        list(Manifest): A list of valid manifests.
    """
    modules = set()

    path = Path.cwd() / path
    path = path.resolve()

    manifest_globs = fast_search_manifests(path)

    check_module = get_filter(filters)

    for path in manifest_globs:
        manifest = Manifest.from_path(path)

        if not check_module(manifest):
            continue

        modules.add(manifest)

    return modules


def find_modules_paths(paths, filters=None, options=None):
    """
    Search modules in multiple paths.


    This can be used to search for odoo modules in different
    addons paths.

    For example, you'd want to discover all odoo modules installed
    in your environment.

    Args:
        paths (list(Path)): list of Path in which the manifest
            lookup occurs.

        filters (Set(str)): Set of filters to ignore some manifests.

        options (object): Object with a flag to exclude core odoo addons.

    Returns:
        list(Manifest): All manifests in all the paths provided.
    """
    modules = set()

    if options and not options.exclude_odoo:
        odoo_path = base_addons_path()
        if odoo_path:
            paths.add(odoo_path)

    for path in paths:
        modules = modules.union(
            find_modules(Path(path), filters=filters)
        )

    return modules


def get_manifest(manifest, render_description=False):
    """
    Shortcut to get a manifest from path.

    # TODO maybe this should be deprecated now.
    """
    return Manifest.from_path(manifest, render_description)


def build_module_dependencies(
    modules,
    modules_lst=False,
    deps=None,
    quiet=True
):
    """
    Generate dependencies of each modules passed in this function.

    When all modules data is loaded, it is then possible to generate
    a graph of all the modules and their dependencies.

    This graph then can be used in a topological sort to guess in which
    correct order the modules should be installed. Based on the
    dependencies, it's also possible to guess which modules are
    required by one other module and find which modules are missing.

    Args:
        modules (list(Manifest)): List of manifest to use for dependencies

        modules_lst (list(Manifest)): List of manifest to build dependencies
            for.

        deps (dict): Initial dependencies

        quiet (bool): Silence missing modules when they're not present in the
            module set.

    Returns:
        dict: A dictionary of {module: [dep,..], ...} of the current set.
    """
    if deps is None:
        deps = {}

    to_process = modules_lst or []

    while len(to_process) > 0:
        cur_module = to_process.pop()
        if cur_module not in modules:
            continue

        dependencies = modules[cur_module].depends
        deps[cur_module] = set(dependencies)

        for dep in dependencies:
            if dep not in deps:
                to_process.append(dep)

            if not quiet and dep not in modules:
                print((
                    "Module {cur_module} depends on {dep} "
                    "which isn't in addons_path"
                ).format(cur_module=cur_module, dep=dep))

    return deps


def build_dependencies(
    modules,
    modules_lst,
    lookup_auto_install=True,
    deps=None,
    quiet=True
):
    """
    Build dependencies with auto installable modules.

    It's more or less the same as build_module_dependencies, but
    it goes a step further by injecting auto dependent modules
    that have all their dependencies in the dependencies looked up
    first.

    This by itself makes it possible to guess the modules that would
    need to be installed given the current addons path and specified
    modules that needs to be checked.

    For example, if you wanted to check for the modules_lst = ['sale', 'stock']

    It would first pull all the dependencies of the module sale, then it would
    pull all the dependencies of the module stock. Then it would lookup
    for all modules that are auto installable. If all of their dependencies are
    in the pulled dependencies. They'd get pulled into the dependencies.

    Then it would check again for auto installable modules if any new
    dependency can pull more auto installable modules.

    Unfortunately, it's not possible to have 100% guarantee that you'll
    get the exact same module set as in odoo. There is a guarantee that all
    the modules found will be installed. But odoo can request more modules
    to be installed as the account module that trigger some extra modules
    to be installed at init time.

    Args:
        modules (list(Manifest)): List of all modules available

        modules_lst (list(Manifest)): List of manifest you want to find their
            dependencies
        lookup_auto_install (bool): Lookup for auto installable modules.

        deps (dict): List of already known dependencies

        quiet (bool): Silence missing dependencies logs

    Returns:
        dict: dict of dependencies of the format {module: [dep1,...], ...}
    """
    deps = build_module_dependencies(
        modules,
        modules_lst,
        deps=deps,
        quiet=quiet
    )

    if not lookup_auto_install:
        return deps

    old_deps_length = 0

    while len(deps) != old_deps_length:
        old_deps_length = len(deps)

        to_install = []

        for name, module in modules.items():
            if not module.auto_install or name in deps:
                continue

            module_deps = module.depends
            for dep in module_deps:
                if dep not in deps:
                    break
            else:
                if len(module_deps) > 0:
                    to_install.append(name)

        deps = build_module_dependencies(
            modules,
            to_install,
            deps=deps,
            quiet=quiet
        )

    return deps


def base_addons_path():
    """
    Find the path of odoo itself.

    Returns:
        Path: Location where odoo is installed.
    """
    odoo_path = (
        module_path("odoo", raise_not_found=False) or
        module_path("openerp", raise_not_found=False)
    )
    return odoo_path


def find_addons_paths(paths, options=False):
    """
    Find addons in provided paths.

    Args:
      paths (List<Path>): A list of paths to search for addons.

    Returns:
      Set<Manifest>: A list of manifests
    """
    filters = set()
    filters.add('installable')

    if options and not options.exclude_odoo:
        odoo_path = base_addons_path()
        if odoo_path:
            paths.add(odoo_path)

    if options and options.include_odoo_entrypoints:
        entry_point = "odoo_addons_paths"
        for ep in pkg_resources.iter_entry_points(group=entry_point):
            functor = ep.load()
            new_paths = functor()

            if new_paths:
                paths |= new_paths

    modules = find_modules_paths(
        paths,
        filters=filters
    )

    found_paths = set()

    for manifest in modules:
        found_paths.add(manifest.path.parent)

    return found_paths
