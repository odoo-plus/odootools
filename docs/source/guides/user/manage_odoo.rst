Odoo Environment Management
===========================

Installing Odoo
---------------

Installing odoo is possible through the command :bash:`manage setup`. Here's a minimal
example:

.. code-block:: bash
    
   odootools manage setup 15.0

.. asciinema:: PJhFfSZHtwv269kWQV2K0JhuM

It will install by default from the repository https://github.com/odoo/odoo and
use the latest commit of the branch 15.0.

If you want to use a more specific version. It's possible to define other
parameters. 

.. list-table:: Parameters
   
   * - Parameter
     - Description

   * - :bash:`--ref`
     - A git ref that points to a commit, branch or tag.

   * - :bash:`--repo`
     - An alternative repository, it could point to a custom
       repository like https://github.com/oca/ocb

   * - :bash:`--release`
     - Tell which release to use based on the release stored in
       https://nightly.odoo.com/

Optimizing your installation
----------------------------

By default, Odoo will get installed with all localization files. Unfortunately, these
files can consume a lot of space and make docker images much larger than they need.

In that case, if you know that you won't need more than certain languages, it's possible
to tell odoo to keep only certain locales with the :bash:`--languages` parameter. 

.. code-block:: bash

    oodotools manage setup --languages fr_CA,en_US 15.0


Searching available odoo modules
--------------------------------

When configuring your environment, it is possible to alter the automatically
discovered :code:`addons_path`. In that case, the modules that can be found
can go beyond the odoo installation itself.

There are multiple :code:`odootools module` subcommands that can be used to know
what's installed in your environment.

Sometimes, it's impossible to install some modules because odoo doesn't seem to
be able to find them. With odoo-tools, you can find the modules and where they
are located. Sometimes, you may end up with 2 modules with the same name but in
different directory. Odoo will not always load the correct module. But odoo-tools
will be able to find both modules and then you'll be ale to either rename a module
or remove the module that you don't need.

The :code:`deps` subcommand let you find dependencies that would get installed
while trying to install a module. If some dependencies are missing, you'll be able
to find out about it before attempting to install it. 

.. code-block:: bash

   # --auto will be able to pull sale_stock from dependencies
   odootools module deps -m website -m sale --auto

Here's a preview of what you can do:

.. asciinema:: aU2z8bXtlUp8G9LmbZyGllb6L


Starting an Odoo interactive shell
----------------------------------

You can start an interactive shell that uses ptpython to access your databases.

.. code-block:: bash

   odootools shell -d test_database


.. asciinema:: KzVqUeW1IvcBP9YN5nIvtTuUe
