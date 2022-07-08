Developer Guide
===============

.. note::

   This isn't complete and will have a lot more updates later.

This section is mainly for developer that would like to use the api exposed
by this library to extend the possibilities of their odoo environment.

If you're willing to do things that Odoo was obviously not designed for, there
are chances that some of the functions in this library will make your life easer.

This library is a collection of utilities that can be used to make a more optimized
environment of odoo. There are reasons why most of the thing you can do with
this library would never get implemented in odoo itself. Odoo is a monolithic
application. Even thought it provides a WSGI interface, it is an intertwined 
cluster of things that can't be completely dissociated easily.

This library won't help you much here but can help you build api that will
be able to automatically manage your modules files, assets or potentially have
a custom API to install/uninstall odoo addons from a backend that's guaranteed
to not crash if odoo itself is crashed.

One big disadvantage of working with a XMLRPC api is that it's highly dependent
on the ability of odoo to even start. This library makes it easier to implement
odoo code that runs without an odoo server at all.

