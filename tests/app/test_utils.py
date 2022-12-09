from odoo_tools.app.utils import OdooVersionedString
from mock import patch, MagicMock


def test_versioned_string():
    version_info = OdooVersionedString("a.b.v{version_info[0]}")

    odoo_release = MagicMock()

    odoo_release.version_info = [15, 0, 0, 0, 0]

    modules = {
        "odoo": MagicMock(),
        "odoo.release": odoo_release,
    }

    with patch("sys.modules", modules):
        assert version_info.get_string() == "a.b.v15"
        assert str(version_info) == "a.b.v15"
