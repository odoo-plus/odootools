from mock import patch, MagicMock
import pytest
from pathlib import Path
from io import BytesIO

from odoo_tools.modules.translate import PoFileReader, PoFileWriter


@pytest.fixture
def modules():
    odoo = MagicMock()
    return {
        "odoo": odoo,
        "odoo.release": odoo.release,
    }


class MockPOFile(object):
    def __init__(self, filename):
        self.filename = filename

    def __iter__(self):
        entry1 = MagicMock()

        occurence1 = "model:ir.model,name:account_debit_note.model_account"
        code = "code:file.py:0"
        sel = "selection:file,model"
        # Strict doesn't include this
        cons = "sql_constraint:abc"
        # will be ignored as invalid
        blarg = "whoa"

        entry2 = MagicMock()
        entry2.obsolete = False
        entry2.occurrences = [
            (occurence1, 100),
            (code, 102),
            # will be ignored as double occurence
            (code, 103),
            (sel, 103),
            (cons, 104),
            (blarg, 105),
        ]

        entries = [
            entry1,
            entry2
        ]

        for entry in entries:
            yield entry

    def merge(self, other):
        pass


def test_po_reader():

    with patch.object(Path, 'exists') as exists, \
         patch('polib.pofile') as pofile, \
         patch('polib.POFile', MockPOFile):

        pofile.side_effect = MockPOFile

        exists.return_value = True

        reader = PoFileReader('test.po', options={'read_pot': True})
        assert reader.pofile.filename == 'test.po'

        entries = [
            entry for entry in reader
        ]

        assert len(entries) == 3

        # parse po as a buffer
        reader = PoFileReader(MagicMock())

        # create reader directly with po file
        reader = PoFileReader(MockPOFile('test.po'))


def test_po_reader_strict():
    with patch.object(Path, 'exists') as exists, \
         patch('polib.pofile') as pofile:

        pofile.side_effect = MockPOFile

        exists.return_value = True

        reader = PoFileReader('test.po', options={'strict': True})
        assert reader.pofile.filename == 'test.po'

        entries = [
            entry for entry in reader
        ]

        assert len(entries) == 2


def test_po_writer(modules):
    buffer = BytesIO()

    with patch.dict('sys.modules', modules):
        writer = PoFileWriter(buffer, 'fr_CA')
        writer.write_rows([
            ('base', 'code', 'file.py', '0', 'yes', 'oui', ''),
            # If translation is the same as source then don't translate it
            ('base', 'code', 'file.py', '0', 'no', 'no', ''),
        ])

        writer.merge(MagicMock())

    # Create pot file
    with patch.dict('sys.modules', modules):
        writer = PoFileWriter(buffer, None)
        writer.write_rows([
            ('base', 'code', 'file.py', '0', 'yes', 'oui', ''),
        ])

        writer.merge(MagicMock())

    # Create pot file
    with patch.dict('sys.modules', modules, pofile=MagicMock()):
        writer = PoFileWriter(buffer, None)
        writer.write_rows([
            ('base', 'code', 'file.py', '0', 'yes', 'oui', ''),
        ])

        writer.merge(MagicMock())
