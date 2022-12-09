import time
import os
import random
import logging
from pathlib import Path
from .request import (
    SessionManagementMixin,
    DbManagementMixin
)


_logger = logging.getLogger(__name__)


class AppMixin(object):
    pass


class SessionStoreMixin(AppMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_store = None
        self.execute_session_gc = False

    # TODO rewrite, it doesn't guarantee that the mixin is implemented
    # it just guarantee that the mixin is in the chain but without any
    # implementation. There should be a check that if this mixin is used
    # the request type must implement this mixin instead.
    def _request_type(self):
        bases = super()._request_type()
        # bases.insert(0, SessionManagementMixin)
        return bases

    @property
    def session_store(self):
        if not self._session_store:
            self._session_store = self.make_session_store()
        return self._session_store

    def session_gc(self):
        pass

    def make_session_store(self):
        raise NotImplementedError("make_session_store not implemented.")


class EnvironmentManagerMixin(AppMixin):
    def dispatch(self, environ, start_response):
        from odoo.api import Environment

        with Environment.manage():
            response = super().dispatch(environ, start_response)

        return response


class DbRequestMixin(AppMixin):
    def _request_type(self):
        bases = super()._request_type()
        bases.insert(0, DbManagementMixin)
        return bases
