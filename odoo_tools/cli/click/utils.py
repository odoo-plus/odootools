import click
from ...compat import Path


def path_complete(ctx, param, incomplete):
    current_path = Path(incomplete)

    if current_path.exists():
        base_path = current_path
    else:
        base_path = current_path.parent

    paths = [str(base_path)]
    for path in base_path.iterdir():
        if path.is_dir():
            paths.append(str(path))

    return paths


class ModuleType(click.ParamType):
    name = "module"

    def convert(self, value, param, ctx):
        if isinstance(value, set):
            return value

        return {
            val.strip()
            for val in value.split(',')
            if val.strip()
        }


MODULE_TYPE = ModuleType()
