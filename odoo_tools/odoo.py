"""
Module
------

Collection of API that can be used to simply manipulate
an odoo environment.

There are multiple use cases in which you'd want to use an api
to manipulate an odoo environment.

Here are a few notable example:

- Setting up a docker image
- Configuring a CI pipeline to run tests
"""
from .api.environment import Environment
