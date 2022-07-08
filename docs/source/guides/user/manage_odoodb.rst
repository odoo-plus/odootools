Odoo Database Management
========================

Listing databases
-----------------

Sometimes, you need to be able to list database or even just verify that
a :code:`dbfilter` actually works. With the :code:`db list` command, you
can list databases based o the odoo version that you want. Filter out
the databases that aren't compatible with the currently installed version
of odoo. Filter the databases that can match a specified dbfilter or even
pass a hostname to check which database matches the dbfilter.

.. code-block:: bash

   $ odootools db list


List only databases that are compatible with odoo version 14.0.

.. code-block:: bash

   $ odootools db list --filter-version 14.0


List all databases that are compatible with the currently installed
version of Odoo and that matches the dbfilter :code:`%d.docker`. In other
words, the databases can be called: :code:`test.docker`.

.. code-block:: bash

   $ odootools db list --dbfilter "%d.docker" --hostname "test.com"

.. asciinema:: wikWwV0BTqNPRVDWJtpXaTv6m

Staring a fresh database
------------------------

When it's time to work with odoo, there's a time you need to start with
a fresh database. It provides a simple command line tool for this particular
purpose. Technically odoo can do most of this on its own, but odoo command
line is more or less trying to start a web server, initialize and update
modules all at once. Instead, odoo-tools provide interface that are
designed to do only one thing.

The `db init` subcommand is one of
those command. It is designed to initialize a database and that's all.
Unlike odoo, odoo-tools will create a database without demo data by
default. From experience, initializing demo data in databases causes 
more issues than it solve. More than often, people want to create a
database they can use and in very specific cases, you'll want to
create a database with demo data loaded to make it easier to test some
features or potentially run unit tests against demo data.

For that reason, demo have to be loaded explicitely, otherwise it can
be the cause of loading demo data in an existing database or wasting
your time to reinitialize odoo without demo after initializing a database
unwillingly with demo data by accident.

The way odoo-tools work, it initialize a database in multiple steps.

1. It will install the base module and its automatically pulled dependencies.
2. When the database is created and initialized with base modules, it will
   configure company data to define a country code if specified.
3. It will install all the remaining modules that were requested to be installed
   during the installation.


Here's an example:

.. code-block:: bash

   $ odootools manage init -m sale,stock -m account --country CA --language fr_CA production_database


.. asciinema:: Tgawl0I16TuWe7NJg7HNM5Nxq


This will initialize a database by installing the modules sale, stock and account. It would set the
country of the res.company to Canada and install the language French Canada. What's important to note
is that setting the country code during the initialization isn't for nothing. The account module
is particular in a way that when it is installed, it will attempt to find the correct `l10n_*` module
to install. If you try to install the account module before setting a proper country code, Odoo will
install the module `l10n_generic_coa` that you may not want to have installed. And when it will
be time to setup accounting for your company, you'll have to manually install the proper `l10n_*`
module for your country. Odoo tools attemps to save you those extra steps by configuring your database
as much as possible during initialization.


Installing new modules
~~~~~~~~~~~~~~~~~~~~~~

Installing new modules can be achieved with the following command line:

.. code-block:: bash

   $ odootools manage install -m website,mrp -m payment production_database

The `-m` option can be used multiple times and can be of the csv format as used in the
odoo command lines. There's a `--force` that will force modules to be initialized
instead of being updated. If a module is already installed, it will simply try to
update it.

.. warning::

   Don't use `--force` unless you have a good reason to have modules to be reinitialized.
   Using the odoo command lines, it's possible to wrongfully reinitialize a module using
   `-i` instead of `-u`. Generally it doesn't cause issues, but there are specific cases
   where it could result have unforseen effect like removing or breaking some data
   relationship. Sometimes it could cause some data to have duplicates. Unless you know
   what you're doing, don't use the `--force` as it can break your database.


Updating modules
~~~~~~~~~~~~~~~~

Updating modules is more or less similar as `manage install` but there are no `--force`
option that could reinitialize modules. If a module specified in update isn't installed,
it will automatically install it.

.. code-block:: bash

   $ odootools manage update -m website


Uninstalling modules
~~~~~~~~~~~~~~~~~~~~

Uninstalling a module can be achieved with the `manage uninstall` command. It has the
same parameters as `manage update`. If for some reasons, odoo cannot start or the website
can't be used to uninstall a module, this command should be able to save the day as it can
uninstall modules on its own. If the module can be uninstalled, a registry change
notification should be triggered to all running instances. And the module should be
sucessfully unloaded from all running instances. If the module isn't installed anymore
and it didn't solve your issues, you may want to restart the broken workers.


.. code-block:: bash

   $ odootools manage uninstall -m website
