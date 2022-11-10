import os
import pytest
from pathlib import Path
from mock import patch
from odoo_tools.api.context import Context


def test_context_default_odoorc(tmp_path):
    new_env = {
        "HOME": str(tmp_path)
    }

    with patch.dict(os.environ, new_env, clear=True):
        ctx = Context()
        assert ctx.default_odoorc() == Path.cwd() / 'odoo.cfg'

    new_env = {
        "HOME": str(tmp_path),
    }

    with patch.dict(os.environ, new_env, clear=True):
        odoo_rc = tmp_path / '.odoorc'
        with odoo_rc.open('w') as fout:
            fout.write('')

        ctx = Context()
        assert ctx.default_odoorc() == odoo_rc

    ctx = Context()
    assert ctx.default_odoorc() == Path.cwd() / 'odoo.cfg'
    assert ctx.odoo_rc == Path.cwd() / 'odoo.cfg'
