import click
from .utils import path_complete
from ...compat import Path


@click.group("path")
def addons_paths():
    pass


@addons_paths.command("ls")
@click.argument(
    'addons_path',
    nargs=-1,
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    shell_complete=path_complete,
    required=False,
    # default=[]
)
@click.option(
    '--sorted',
    help="Sort paths",
    is_flag=True,
    default=False
)
@click.pass_context
def list_addons_paths(ctx, addons_path, sorted):
    env = ctx.obj['env']

    if addons_path:
        for path in addons_path:
            env.context.custom_paths.add(path)

        env.context.force_addons_lookup = True

    paths = env.addons_paths()

    if sorted:
        paths = list(paths)
        paths.sort()

    for path in paths:
        print(path)


@addons_paths.command("add")
@click.argument(
    'addons_path',
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
)
@click.pass_context
def add_addons_path(ctx, addons_path):
    env = ctx.obj['env']

    env.context.custom_paths.add(addons_path)
    env.context.force_addons_lookup = True

    paths = [
        str(path)
        for path in env.addons_paths()
    ]

    with env.config() as config:
        config.set(
            'options',
            'addons_path',
            ",".join(paths)
        )


@addons_paths.command("rm")
@click.argument(
    'addons_path',
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
)
@click.pass_context
def remove_addons_path(ctx, addons_path):
    env = ctx.obj['env']

    remove_path = Path(addons_path)

    paths = [
        str(path)
        for path in env.addons_paths()
        if path != remove_path
    ]

    with env.config() as config:
        config.set(
            'options',
            'addons_path',
            ",".join(paths)
        )
