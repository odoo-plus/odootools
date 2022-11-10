import pytest
import click
from mock import patch, call, MagicMock

from odoo_tools.cli.registry import CommandRegistry


def test_empty_registry():
    registry = CommandRegistry()

    with pytest.raises(KeyError):
        registry.get('gen')

    assert len(registry.groups) == 0


def test_register_command(runner):

    @click.group()
    def main():
        pass

    @click.group()
    def my_group():
        pass

    @click.command()
    def my_cmd():
        print('my-cmd1')

    @click.command()
    def my_cmd2():
        print('my-cmd2')

    registry = CommandRegistry()

    ep = MagicMock()
    ep.load.return_value = my_group
    ep.name = 'my_group'

    ep2 = MagicMock()
    ep2.load.return_value = my_cmd
    ep2.name = 'my_group'

    with patch('odoo_tools.cli.registry.iter_entry_points') as it:
        it.side_effect = [[ep], [ep2]]
        registry.register_commands()

    assert len(registry.groups) == 1

    registry.set_main(main)

    my_group2 = registry.get('my_group')
    assert my_group == my_group2

    registry.load()
    assert len(registry.loaded) == 1

    registry.load()
    assert len(registry.loaded) == 1

    result = runner.invoke(
        main,
        [
            'my-group',
            'my-cmd',
        ]
    )

    assert result.exception is None
    assert result.output == 'my-cmd1\n'

    result = runner.invoke(
        main,
        [
            'my-group',
            'my-cmd2',
        ]
    )

    assert isinstance(result.exception, SystemExit)

    ep3 = MagicMock()
    ep3.load.return_value = my_cmd2
    ep3.name = 'my_group'

    with patch('odoo_tools.cli.registry.iter_entry_points') as it:
        it.side_effect = [[], [ep3]]
        registry.register_commands()

    result = runner.invoke(
        main,
        [
            'my-group',
            'my-cmd2',
        ]
    )

    assert result.exception is None
    assert result.output == 'my-cmd2\n'
