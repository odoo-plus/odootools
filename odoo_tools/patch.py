import sys
import weakref
import gc


def unload_modules(module_name, unload_submodules=True):
    """
    Remove the module or the module and its submodules from sys.modules

    Unloading a module can be used to remove all traces of a module in
    sys.modules and all the refference to the modules including circular
    references.

    Odoo can import odoo.models from odoo and import odoo from models. In
    that case, python isn't smart enough to garbage collect the reference
    island. This function can find all references and will attempt to
    remove everything that it can in hope that this will be enough
    for the gc to clean up the rest.

    For example this:

    .. code:: python

        import odoo
        unload_modules('odoo') # this will remove all odoo.* from sys
        # here odoo shouldn't reference anything

    .. caution::

        When removing a module from sys.modules it doesn't guarantee
        that all references of the modules are gone. It simply guarantee
        that the module can be reimported.

        Dangling references can prevent imported modules from being garbage
        collected or said differently this will create a memory leak.
    """
    submodule_filter = "{}.".format(module_name)

    modules = [
        mod
        for mod in sys.modules.keys()
        if (
            mod == module_name or
            (unload_submodules and mod.startswith(submodule_filter))
        )
    ]

    weakrefs = [
        weakref.ref(sys.modules[mod])
        for mod in modules
    ]

    for mod in modules:
        del sys.modules[mod]

    for ref in weakrefs:
        if ref() is None:
            # It's already cleaned
            continue

        referrers = gc.get_referrers(ref())
        id_ref = id(ref())
        for refferer in referrers:
            if isinstance(refferer, dict):
                to_remove = [
                    key
                    for key, val in refferer.items()
                    if id(val) == id_ref
                ]
                for key in to_remove:
                    del refferer[key]

        if ref() is not None:
            print(
                f"Couldn't completely unload {ref()} with "
                f"{len(gc.get_referrers(ref()))}"
            )
