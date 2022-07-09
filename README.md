# Odoo Tools

[![Python package](https://github.com/llacroix/odoo-tools/actions/workflows/python-package.yml/badge.svg)](https://github.com/llacroix/odoo-tools/actions/workflows/python-package.yml)
[![codecov](https://codecov.io/gh/llacroix/odoo-tools/branch/main/graph/badge.svg?token=MdWK5ZC2ab)](https://codecov.io/gh/llacroix/odoo-tools)


A library that provide command line tools to manage an Odoo
environment. The main purpose of the library is to provide
a programmatic API that lets you build tools to automate
management of odoo environment.

## How to install

    pip install odoo-tools

## Documentation

You can check the documentation hosted [here](https://odoo-tools.readthedocs.io/en/latest/).


## Example of use

It can be used to find modules in addons paths. It can be
used to discover addons paths in directory in a way to provide
an easy way to manage odoo.cfg files without having to break your
head managing things.

For example remove all modules that can't be installed in every
configured addons paths:

    env = Environment()

    for module in env.modules.list(filters={'non_installable'}):
        module.remove()


Define addons paths based on paths in /var/lib/addons:

    env = Environment()
    env.context.custom_paths.add(Path("/var/lib/addons"))
    env.set_config('addons_path', env.addons_paths())

This will not simply add `/var/lib/addons` to the `addons_path`. It
will search into this folder for directories that have installable
addons in them. `addons_paths()` returns all possible addons paths
detected based on the environment variables, odoorc file and actual
state of the environment. So it returns everything you need to start
odoo later.
