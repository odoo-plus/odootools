import pkg_resources
from collections import defaultdict

custom_entrypoints = defaultdict(list)


def execute_entrypoint(name, env):
    for ep in pkg_resources.iter_entry_points(group=name):
        functor = ep.load()
        functor(env)

    for ep in custom_entrypoints.get(name, []):
        ep(env)


def entrypoint(name):
    def wrap(func):
        if func not in custom_entrypoints[name]:
            custom_entrypoints[name].append(func)
        return func
    return wrap
