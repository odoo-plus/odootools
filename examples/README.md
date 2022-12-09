How to use the custom odoo server
=================================

It's possible to call OdooServer using gunicorn and the gevent workers.

You need to modify the script `odoo_server.py` and change the variable `base_path_odoo`
to point to a path in which Odoo is cloned for example.

Or simply clone odoo in the current folder without changing the script itself.

    git clone https://github.com/odoo/odoo odoo

Then call odoo with:

    gunicorn --worker-class=gevent --timeout 600 "odoo_server:handler"

This will start a gunicorn server on the http://localhost:8000 and spawn gevent workers.  For
that reason, the longpolling interfaces should just work. The timeout is set to 600 second, but
it can be decreased to something smaller.
