import sys
import click
import json
from toposort import toposort_flatten
from .utils import path_complete
from ...compat import Path
from ...modules.search import build_dependencies


@click.group()
def module():
    pass


@module.command("ls")
@click.option(
    '--only-name',
    default=False,
    help="Only display module name instead of path",
    is_flag=True
)
@click.option(
    '--csv',
    default=False,
    help="Only display module name instead of path",
    is_flag=True
)
@click.option(
    '--installable',
    help="Output only installable modules",
    is_flag=True,
    default=False
)
@click.option(
    '--non-installable',
    help="Output only non installable modules",
    is_flag=True,
    default=False
)
@click.option(
    '--without-version',
    help="Display only modules without versions",
    is_flag=True,
    default=False
)
@click.option(
    '-m',
    '--modules',
    help="Only return modules that matches the provided module names.",
    multiple=True
)
@click.option(
    '-p',
    '--path',
    help="Location in which to search",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    shell_complete=path_complete,
    multiple=True

)
@click.option(
    '--sorted',
    help="Sort module in alphabetical number",
    is_flag=True
)
@click.pass_context
def list_modules(
    ctx,
    only_name,
    csv,
    installable,
    non_installable,
    without_version,
    modules,
    path,
    sorted
):
    env = ctx.obj['env']

    if path:
        env.context.force_addons_lookup = True
        for _path in path:
            env.context.custom_paths.add(
                Path(_path)
            )

    filters = set()

    if installable:
        filters.add('installable')

    if non_installable:
        filters.add('non_installable')

    def check_module(mod):
        ret = True

        if without_version:
            ret = ret and 'version' in mod

        if modules:
            ret = ret and mod.path.name in modules

        return ret

    mods = [
        mod.technical_name if only_name else str(mod)
        for mod in env.modules.list(filters=filters)
        if check_module(mod)
    ]

    if sorted:
        mods.sort()

    if csv:
        print(",".join(mods))
    else:
        for mod in mods:
            print(mod)


@module.command("show")
@click.argument(
    'module'
)
@click.pass_context
def show_module(ctx, module):
    env = ctx.obj['env']

    mods = env.modules.list()

    for mod in mods:
        if mod.path.name == module:
            break
    else:
        print("Module {} not found".format(module))
        sys.exit(1)

    print(json.dumps(mod.values()))


@module.command("deps")
@click.option(
    '--only-name',
    default=False,
    help="Only display module name instead of path",
    is_flag=True
)
@click.option(
    '--csv',
    default=False,
    help="Only display module name instead of path",
    is_flag=True
)
@click.option(
    '--installable',
    help="Output only installable modules",
    is_flag=True,
    default=False
)
@click.option(
    '--non-installable',
    help="Output only non installable modules",
    is_flag=True,
    default=False
)
@click.option(
    '--without-version',
    help="Display only modules without versions",
    is_flag=True,
    default=False
)
@click.option(
    '-m',
    '--modules',
    help="Only return modules that matches the provided module names.",
    multiple=True
)
@click.option(
    '--csv-modules',
    help="Find all dependencies for modules input as csv",
    default=""
)
@click.option(
    '-p',
    '--path',
    help="Location in which to search",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    shell_complete=path_complete,
    multiple=True

)
@click.option(
    '--auto',
    help="Include auto installed modules",
    is_flag=True
)
@click.option(
    '--include-modules',
    help="Remove logs and warnings.",
    is_flag=True,
    default=False
)
@click.option(
    '--quiet',
    help="Remove logs and warnings.",
    is_flag=True,
    default=False
)
@click.pass_context
def show_dependencies(
    ctx,
    only_name,
    csv,
    installable,
    non_installable,
    without_version,
    modules,
    csv_modules,
    path,
    auto,
    quiet,
    include_modules
):
    env = ctx.obj['env']

    if path:
        env.context.force_addons_lookup = True
        for _path in path:
            env.context.custom_paths.add(
                Path(_path)
            )

    filters = set()

    if installable:
        filters.add('installable')

    if non_installable:
        filters.add('non_installable')

    def check_module(mod):
        ret = True

        if without_version:
            ret = ret and 'version' in mod

        return ret

    check_modules = list(modules) + [
        mod.strip()
        for mod in csv_modules.split(',')
        if mod.strip()
    ]

    modules_kv = {
        mod.path.name: mod
        for mod in env.modules.list(filters=filters)
        if check_module(mod)
    }

    dependencies = build_dependencies(
        modules_kv,
        check_modules[:],
        lookup_auto_install=auto,
        quiet=quiet
    )

    sorted_dependencies = []
    for dep in toposort_flatten(dependencies):
        if not include_modules and dep in modules:
            continue
        try:
            sorted_dependencies.append(modules_kv[dep])
        except KeyError:
            pass

    mods = [
        mod.path.name if only_name else str(mod)
        for mod in sorted_dependencies
    ]

    if csv:
        print(",".join(mods), end="")
    else:
        for mod in mods:
            print(mod)


@module.command(
    help="List requirements required by modules in addons_paths"
)
@click.option(
    '--exclude',
    help="Exclude file paths",
    multiple=True
)
@click.option(
    '-p',
    '--path',
    help="Add custom requirements file path",
    multiple=True
)
@click.option(
    '--add-rule',
    help="Add extra requirements rule",
    multiple=True
)
@click.option(
    '--package-map',
    help="Package map to resolve some modules that can't be installed",
)
@click.option(
    '--lookup-requirements',
    help=(
        "Lookup recursively requirements in addons_paths for a file "
        "named requirements.txt"
    ),
    is_flag=True,
    default=False
)
@click.option(
    '--sort',
    help="Sort requirements in alphabetical order",
    is_flag=True,
    default=False
)
@click.pass_context
def requirements(
    ctx,
    exclude,
    path,
    add_rule,
    package_map,
    lookup_requirements,
    sort
):
    env = ctx.obj['env']
    env.context.package_map_file = package_map

    found_files = env.requirement_files()

    for file_path in path:
        if file_path not in exclude:
            found_files.add(file_path)

    package_maps = env.package_map()

    requirements = env.modules.requirements(
        package_map=package_maps,
        extra_paths=found_files,
        extra_rules=set(add_rule)
    )

    if sort:
        requirements = [req for req in requirements]
        requirements.sort()

    print("\n".join(requirements))
