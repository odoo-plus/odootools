from odoo_tools.modules.search import find_addons_paths
from odoo_tools.api.objects import Manifest
from mock import patch, MagicMock


def test_find_paths_entrypoint(tmp_path):
    mocked_path = tmp_path / 'mocked'

    def mocked_iter_entrypoints():
        mock_entrypoint = MagicMock()

        mock_entrypoint.load.return_value = lambda: {mocked_path}

        return [mock_entrypoint]

    with patch('pkg_resources.iter_entry_points') as mock_pkg:
        mock_pkg.return_value = mocked_iter_entrypoints()

        options = MagicMock()
        options.include_odoo_entrypoints = True

        res = find_addons_paths(set(), options)

        assert res == set()

        manifest = Manifest(mocked_path / 'mod')
        manifest.save()

        res = find_addons_paths(set(), options)

        assert res == set([mocked_path])
