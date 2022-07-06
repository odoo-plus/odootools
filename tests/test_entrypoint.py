from mock import MagicMock, patch
from odoo_tools.entrypoints import execute_entrypoint, entrypoint, custom_entrypoints


def test_entrypoint():

    @entrypoint("test")
    def super_entrypoint(manage):
        manage.called += 1

    ctx = MagicMock()
    ctx.called = 0
    execute_entrypoint("toast", ctx)
    assert ctx.called == 0

    ctx = MagicMock()
    ctx.called = 0
    execute_entrypoint("test", ctx)
    assert ctx.called == 1

    custom_entrypoints['test'] = []


def test_entrypoint_pkg():

    def mocked_iter_entrypoints():
        mock_entrypoint = MagicMock()

        def cb(ctx):
            ctx.called += 1

        mock_entrypoint.load.return_value = cb

        return [mock_entrypoint]

    with patch('pkg_resources.iter_entry_points') as mock_pkg:
        mock_pkg.return_value = mocked_iter_entrypoints()

        ctx = MagicMock()
        ctx.called = 0
        execute_entrypoint("test2", ctx)

        assert ctx.called == 1
