from odoo_tools.api.objects import get_translation_filename


def test_trans_filename():
    assert get_translation_filename('fr_CA', 'bus') == 'fr_CA.po'
    assert get_translation_filename('fr_FR', 'bus') == 'fr.po'
    assert get_translation_filename('', 'bus') == 'bus.pot'
    assert get_translation_filename(None, 'bus') == 'bus.pot'
    assert get_translation_filename(False, 'bus') == 'bus.pot'
