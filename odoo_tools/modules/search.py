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
    return manifest.installable


def filter_noninstallable(manifest):
    return not filter_installable(manifest)


def filter_python_dependencies(manifest):
    if (
        manifest.external_dependencies and
        manifest.external_dependencies.get('python')
    ):
        return True
    else:
        return False


def get_filter(filter_names):
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
    modules = set()

    path = Path.cwd() / path

    manifest_globs = fast_search_manifests(path)

    check_module = get_filter(filters)

    for path in manifest_globs:
        manifest = Manifest.from_path(path)

        if not check_module(manifest):
            continue

        modules.add(manifest)

    return modules


def find_modules_paths(paths, filters=None, options=None):
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
    return Manifest.from_path(manifest, render_description)


def build_module_dependencies(
    modules,
    modules_lst=False,
    deps=None,
    quiet=True
):
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
            paths |= new_paths

    modules = find_modules_paths(
        paths,
        filters=filters
    )

    found_paths = set()

    for manifest in modules:
        found_paths.add(manifest.path.parent)

    return found_paths
