import click
import sys
from ptpython.repl import embed

from ...compat import Path


@click.command()
@click.option(
    '-c',
    '--config',
    help="Config file"
)
@click.argument(
    'params',
    nargs=-1,
)
@click.pass_context
def shell(ctx, config, params):
    env = ctx.obj['env']
    try:
        import odoo
        from odoo.tools import config as odoo_config
        from odoo.api import Environment
        from contextlib import contextmanager, closing
        from odoo.release import version_info
    except ImportError:
        print("Odoo doesn't seem to be installed. Check your path")
        sys.exit(0)

    @contextmanager
    def manage():
        if version_info[0] >= 15:
            yield
        else:
            with Environment.manage():
                yield

    if config:
        odoo_config.config_file = str(Path.cwd() / config)
    else:
        odoo_config.config_file = env.context.odoo_rc

    odoo_config.parse_config(list(params))

    context = {}

    class ProtectedDict(dict):
        def __init__(self, protected_values):
            self.protected_values = protected_values

            super(ProtectedDict, self).__init__(
                **protected_values
            )

        def __setitem__(self, key, value):
            if key in self.protected_values:
                return
            super(ProtectedDict, self).__setitem__(key, value)

    with manage():
        registry = odoo.registry(odoo_config['db_name'])

        with closing(registry.cursor()) as cr:
            env = Environment(cr, 1, context)

            global_vals = {}
            local_vals = ProtectedDict({
                "env": env,
                "registry": registry,
                "cr": cr,
                "context": context
            })

            ret = embed(global_vals, local_vals)

    sys.exit(ret)
