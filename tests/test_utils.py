import pytest
import mock
from mock import patch, call
from pathlib import Path

from odoo_tools.utils import (
    to_path_list,
    is_subdir_of,
    filter_excluded_paths,
    convert_env_value,
    random_string,
    ProtectedDict
)


def test_to_path_list():
    lst = ['/a', 'b', '.c']
    pl = to_path_list(lst)

    for x in pl:
        assert isinstance(x, Path)

    pl = to_path_list([])
    assert len(pl) == 0
    assert isinstance(pl, list)


def test_is_subdir_of():
    a = Path('/a/b')
    b = Path('/a/b/c')
    c = Path('/b/c/d')

    assert is_subdir_of(a, b) is True
    assert is_subdir_of(b, a) is False
    # Non common root
    assert is_subdir_of(b, c) is False
    assert is_subdir_of(c, b) is False


def test_filter_excluded_paths():
    paths = [
        "/a",
        "/b",
        "/a/b",
        "/a/b/c",
        "/b/d/e",
    ]

    res = filter_excluded_paths(paths, to_path_list(['/b/d', '/a']))

    assert res == ['/b']


def test_convert_env_value():
    assert convert_env_value('test', 'True') is True
    assert convert_env_value('test', 'False') is False
    assert convert_env_value('test', 'FALSE') == 'FALSE'
    assert convert_env_value('test', 'TRUE') == 'TRUE'
    assert convert_env_value('test', '1') == '1'


def test_random_string():
    rand1 = random_string(10)
    rand2 = random_string(10)
    rand3 = random_string(10)
    rand4 = random_string(64)
    rand5 = random_string(64)
    rand6 = random_string(64)

    assert rand1 != rand2
    assert rand2 != rand3
    assert rand4 != rand5
    assert rand6 != rand3

    assert len(rand1) == 10
    assert len(rand2) == 10
    assert len(rand3) == 10

    assert len(rand4) == 64
    assert len(rand5) == 64
    assert len(rand6) == 64

    with patch('odoo_tools.utils.random') as random, \
         patch('odoo_tools.utils.range') as ranges:
        ranges.return_value = range(10)
        random.choice.return_value = '1'
        random_string(10)
        assert random.choice.call_count == 10
        ranges.assert_has_calls([call(10)])


def test_protected_dict():
    vals = ProtectedDict(
        protected_values=dict(
            key=1,
            value=2
        )
    )

    assert vals['key'] == 1
    assert vals['value'] == 2

    assert 'key' in vals
    assert 'value' in vals
    assert 'msg' not in vals

    vals['key'] = 2
    vals['value'] = 3
    vals['msg'] = 4

    assert vals['key'] == 1
    assert vals['value'] == 2
    assert vals['msg'] == 4
