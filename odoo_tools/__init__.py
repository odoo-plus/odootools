"""
Overview
========

This library came to light while developing entrypoints
for self configuring docker image. Some of the initial
functions were to search for odoo addons paths and search
for files like requirements.txt and apt-package.txt to
install python libraries the same way OdooSH_ does.

Then internally, some continuous integration tools shared
a lot of those functions that were initially duplicated in
both projects. Eventually, it became obvious that it would
be easier to have a single library that could be used by
both projects.

Then more things were added like the capacity to modify
manifest files programmatically, a shell using ptpython
to quickly enter a python shell with a properly
setup odoo environment, entrypoints from the docker image,
db api to initialize or manage an existing database,
translation tools to generate po and pot files.

This library can be used as is with the available command
lines to manage things manually, but its real purpose is
to be used in an automated environment.

And one thing that's particular is that this library
doesn't require odoo to function for most things. You
can use it to actually install odoo since odoo doesn't
provide easily installable pypi packages unfortunately.

.. _OdooSH: https://odoo.sh
"""
