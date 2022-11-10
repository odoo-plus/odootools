from pkg_resources import iter_entry_points


class CommandRegistry(object):
    def __init__(self):
        self.groups = {}
        self.main_command = None
        self.loaded = set()

    def set_main(self, command):
        self.main_command = command

    def get(self, name):
        return self.groups[name]

    def register(self, name, command):
        self.groups[name] = command

    def register_commands(self):
        for ep in iter_entry_points(group='odootools.command'):
            self.register(ep.name, ep.load())

        for ep in iter_entry_points(group='odootools.command.ext'):
            command = self.groups[ep.name]
            obj = ep.load()
            command.add_command(obj)

    def load(self):
        for key, value in self.groups.items():
            if key in self.loaded:
                continue
            self.loaded.add(key)
            self.main_command.add_command(value)


registry = CommandRegistry()
registry.register_commands()
