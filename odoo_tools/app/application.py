from ..api.environment import Environment
from .plugins import InitOdooPlugin, LoggingPlugin, OverlayModulePlugin


class OdooApplication(object):

    def __init__(self, env=None, plugins=None):
        if env is None:
            env = Environment()

        if plugins is None:
            plugins = []

        self.env = env
        self.loaded = False
        self.plugins = []
        self.application = None

        for plugin in plugins:
            self.add_plugin(plugin)

    def execute_plugin_method(self, method):
        for plugin in self.plugins:
            if hasattr(plugin, method):
                getattr(plugin, method)()

    def load(self):
        if self.loaded:
            return

        self.execute_plugin_method('prepare_environment')
        self.execute_plugin_method('init_environment')
        self.execute_plugin_method('postinit_environment')

        self.loaded = True

    def register_defaults(self):
        self.add_plugin(OverlayModulePlugin())
        self.add_plugin(InitOdooPlugin())
        self.add_plugin(LoggingPlugin())

    def add_plugin(self, plugin):
        if hasattr(plugin, "register"):
            plugin.register(self)

        self.plugins.append(plugin)
