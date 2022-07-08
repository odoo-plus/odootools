Odoo Configuration
==================


The odoo configuration file
---------------------------

By default, odoo-tools will search for configuration located in the path as
defined as the environment variable ODOORC. When ODOORC isn't defined, it will
look for files located in the current working directory, then in the home
directory and possibly in `/var/lib/odoo` if `/var/lib/odoo` isn't the home
directory as defined with the `HOME` environment variable.

It will search in all those forders in that order for the files:

- .odoorc
- .openerp_serverrc
- odoo.cfg

In the case, none of the file could be found in any of the possible folder
to look up into. It will default to odoo.cfg in the current working directory.

Listing configurations
----------------------

Listing configuration that are defined in the configuration file can be done using
the following command line:

.. code-block:: bash

   $ odootools config ls
   options.workers = 4
   queue_job.channels = root:2

It's also possible to get individual configurations by accessing directly using the
configuration key. By default it will get settings in the `options` section of the
configuration file.

.. code-block:: bash

   $ odootools config get workers
   4

If you want to get a configuration in a different section, you can pass the `--section`
option to the command line to get a specific section.

.. code-block:: bash

   $ odootools config get --section queue_job channels
   root:2


Modifying configurations
------------------------

The configuration settings can be modified with the `set` subcommand. If you wanted
to change the amount of workers to 8, you could simply use the following command line:

.. code-block:: bash

   $ odootools config set workers 8

As with the `get` subcommand, the default section will be the `options` section. But it's
also possible to define a value in a different section using the `--section` option.

You could change the channels of the `queue_job` configuration to something else with the
following command line:

.. code-block:: bash

   $ odootools config set --section queue_job channels root:1

Configuring addons paths
------------------------

Adding paths
~~~~~~~~~~~~

Addons paths can be modified in a semi automatic ways. You can use the `path` subcommand
to manage the addons paths in your environment.

The subcommand `path add` can be used to populate the configuration `options.addons_paths`
with all folders contained in the provided path. 

Let say you have git project containing sub projects. You could add each of the projects
one by one in the addons paths using:

.. code-block:: bash

   $ odootools path add ./myproject/subproject_a
   $ odootools path add ./myproject/subproject_b
   $ odootools path add ./myproject/subproject_c
   $ odootools path add ./myproject

But odoo-tools is able to introspect recursively all folders containing odoo addons. For that
reason, there is no need to specify sub folders as each of them will get added
automatically when calling:

.. code-block:: bash

   $ odootools path add ./myproject


When done, it will add each of the found path into the active configuration file.

.. note::

   If a folder doesn't contain any directory with odoo addons. It will not get added to
   the addons paths. It doesn't save path that might potentially have addons in the future.


Removing paths
~~~~~~~~~~~~~~

Removing paths can be achieved by calling the `path rm` sub command.

.. code-block:: bash

   $ odootools path rm [full path]/myproject/subproject_b

.. note::

   Using relative path pointing to the same path isn't currently possible to remove
   paths. So use the path shown in the output of `path ls`.

Listing addons_paths
~~~~~~~~~~~~~~~~~~~~

In order to show addons paths, it's possible to use the `path ls` sub command. 

.. code-block:: bash

   $ odootools path ls

This subcommand provide multiple options such as `--sorted` to output paths in alphabetical
order.
