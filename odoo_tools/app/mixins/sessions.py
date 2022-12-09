import os
import random
import time
from pathlib import Path
import logging

from .app import SessionStoreMixin

_logger = logging.getLogger(__name__)


class FileSystemSessionStoreMixin(SessionStoreMixin):
    def __init__(self, application):
        super().__init__(application)
        self.session_dir = Path.cwd()
        self.execute_session_gc = True

    def make_session_store(self):
        from odoo.http import Session, sessions

        _logger.debug('HTTP sessions stored in: %s', self.session_dir)

        if self.execute_session_gc:
            _logger.info('Default session GC disabled, manual GC required.')

        return sessions.FilesystemSessionStore(
            str(self.session_dir),
            session_class=Session,
            renew_missing=True
        )

    def session_gc(self, delta=60*60*24*7):
        if random.random() > 0.001:
            return

        # we keep session one week
        last_week = time.time() - delta
        for fname in os.listdir(self.session_store.path):
            path = os.path.join(self.session_store.path, fname)
            try:
                if os.path.getmtime(path) < last_week:
                    os.unlink(path)
            except OSError:
                pass
