import importlib
import logging

_logger = logging.getLogger(__name__)


ROUTING_KEYS = {
    'defaults', 'subdomain', 'build_only', 'strict_slashes', 'redirect_to',
    'alias', 'host', 'methods',
}


def submap(mapping, keys):
    """
    Get a filtered copy of the mapping where only some keys are present.
    :param Mapping mapping: the original dict-like structure to filter
    :param Iterable keys: the list of keys to keep
    :return dict: a filtered dict copy of the original mapping
    """
    keys = frozenset(keys)
    return {key: mapping[key] for key in mapping if key in keys}


def _generate_routing_rules(modules, nodb_only, converters=None):
    """
    Two-fold algorithm used to (1) determine which method in the
    controller inheritance tree should bind to what URL with respect to
    the list of installed modules and (2) merge the various @route
    arguments of said method with the @route arguments of the method it
    overrides.
    """
    import inspect
    import functools
    from odoo.http import route

    # Preload addons needed
    for mod in modules:
        if not mod:
            continue
        importlib.import_module(f"odoo.addons.{mod}")

    try:
        from odoo.http import Controller
        controllers_registry = Controller.children_classes
    except Exception:
        from odoo.http import controllers_per_module
        controllers_registry = {
            module: [
                ctrl_class for name, ctrl_class in classes
            ]
            for module, classes in controllers_per_module.items()
        }

    def is_valid(cls):
        """ Determine if the class is defined in an addon. """
        path = cls.__module__.split('.')
        return path[:2] == ['odoo', 'addons'] and path[2] in modules

    def get_leaf_classes(cls):
        """
        Find the classes that have no child and that have ``cls`` as
        ancestor.
        """
        result = []
        for subcls in cls.__subclasses__():
            if is_valid(subcls):
                result.extend(get_leaf_classes(subcls))
        if not result and is_valid(cls):
            result.append(cls)
        return result

    def unique(it):
        """ "Uniquifier" for the provided iterable: will output each element of
        the iterable once.
        The iterable's elements must be hashahble.
        :param Iterable it:
        :rtype: Iterator
        """
        seen = set()
        for e in it:
            if e not in seen:
                seen.add(e)
                yield e

    def build_controllers():
        """
        Create dummy controllers that inherit only from the controllers
        defined at the given ``modules`` (often system wide modules or
        installed modules). Modules in this context are Odoo addons.
        """
        # Controllers defined outside of odoo addons are outside of the
        # controller inheritance/extension mechanism.
        yield from (ctrl() for ctrl in controllers_registry.get('', []))

        # Controllers defined inside of odoo addons can be extended in
        # other installed addons. Rebuild the class inheritance here.
        highest_controllers = []
        for module in modules:
            highest_controllers.extend(controllers_registry.get(module, []))

        for top_ctrl in highest_controllers:
            leaf_controllers = list(unique(get_leaf_classes(top_ctrl)))

            name = top_ctrl.__name__
            if leaf_controllers != [top_ctrl]:
                name += ' (extended by %s)' % ', '.join(
                    bot_ctrl.__name__
                    for bot_ctrl in leaf_controllers
                    if bot_ctrl is not top_ctrl
                )

            Ctrl = type(name, tuple(reversed(leaf_controllers)), {})
            yield Ctrl()

    for ctrl in build_controllers():
        for method_name, method in inspect.getmembers(ctrl, inspect.ismethod):

            # Skip this method if it is not @route decorated anywhere in
            # the hierarchy
            def is_method_a_route(cls):
                func = getattr(cls, method_name, None)

                routing = getattr(func, 'original_routing', None)
                if routing is None:
                    routing = getattr(func, 'routing', None)
                    if routing is not None:
                        setattr(func, 'original_routing', routing)
                return routing is not None

            if not any(map(is_method_a_route, type(ctrl).mro())):
                continue

            merged_routing = {
                # 'type': 'http',  # set below
                'auth': 'user',
                'methods': None,
                'routes': [],
                'readonly': False,
            }
            # ancestors first
            for cls in unique(reversed(type(ctrl).mro()[:-2])):
                if method_name not in cls.__dict__:
                    continue
                submethod = getattr(cls, method_name)

                if not hasattr(submethod, 'original_routing'):
                    _logger.warning(
                        (
                            "The endpoint %s is not decorated by @route(), "
                            "decorating it myself."
                        ),
                        f'{cls.__module__}.{cls.__name__}.{method_name}'
                    )
                    submethod = route()(submethod)

                # Ensure "type" is defined on each method's own routing,
                # also ensure overrides don't change the routing type.
                default_type = submethod.original_routing.get('type', 'http')
                routing_type = merged_routing.setdefault('type', default_type)
                original_routing_type = submethod.original_routing.get('type')
                if (
                    original_routing_type not in (None, routing_type)
                ):
                    _logger.warning(
                        (
                            "The endpoint %s changes the route type, using "
                            "the original type: %r."
                        ),
                        f'{cls.__module__}.{cls.__name__}.{method_name}',
                        routing_type
                    )
                submethod.original_routing['type'] = routing_type

                merged_routing.update(submethod.original_routing)

            if not merged_routing['routes']:
                _logger.warning(
                    "%s is a controller endpoint without any route, skipping.",
                    f'{cls.__module__}.{cls.__name__}.{method_name}'
                )
                continue

            if nodb_only and merged_routing['auth'] != "none":
                continue

            for url in merged_routing['routes']:
                # duplicates the function (partial) with a copy of the
                # original __dict__ (update_wrapper) to keep a reference
                # to `original_routing` and `original_endpoint`, assign
                # the merged routing ONLY on the duplicated function to
                # ensure method's immutability.
                endpoint = functools.partial(method)
                functools.update_wrapper(endpoint, method)
                endpoint.routing = merged_routing

                yield (url, endpoint)
