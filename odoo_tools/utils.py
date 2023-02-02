import string
import random
from .compat import Path
import configparser
from configparser import _UNSET
from .utilities.config import parse_value


def to_csv(delimiter=','):
    """
    Convert a iterable of items into a csv of their string representation.
    """

    def serializer(value):
        return delimiter.join([
            str(elem)
            for elem in value
        ])

    return serializer


def from_bool(value):
    """
    Convert a bool into a string value.
    """
    return str(value)


def to_bool(value):
    """
    Convert a string into a bool value.
    """
    if value:
        return value.lower() == 'true'
    else:
        return False


def obj_set(delimiter=',', container=list, item_type=str):
    """
    Convert a CSV value into a set of values.

    Args:
        delimiter (str): the delimiter of the CSV value.

        container (callable): The type of the container of the set.
            Defaults to :obj:`list`.

        item_type (callable): The type of the value to be mapped to.
            Defaults to :obj:`str`.

    Returns:
        container<item_type>: The mapped value of the csv.
    """

    def deserializer(value):
        value = value or ''
        items = value.split(delimiter)

        value = [
            item_type(item.strip())
            for item in items
            if item.strip()
        ]

        return container(value)

    return deserializer


def to_path_list(paths):

    return [
        Path(path)
        for path in paths
    ]


def is_subdir_of(path1, path2):
    try:
        path2.relative_to(path1)
    except ValueError:
        return False
    else:
        return True


def filter_excluded_paths(paths, excluded_paths):
    res_paths = []

    for vpath in paths:
        cur_path = Path(vpath)
        for ex_path in excluded_paths:
            if is_subdir_of(ex_path, cur_path):
                break
        else:
            res_paths.append(vpath)

    return res_paths


def convert_env_value(name, value):
    if value in ['True', 'False']:
        return value == 'True'

    return value


def random_string(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


class ConfigParser(configparser.RawConfigParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, section, option, *, raw=False, vars=None, fallback=_UNSET):
        if (
            (
                section not in self._sections or
                option not in self._sections[section]
            ) and
            self._defaults and
            option in self._defaults
        ):
            return parse_value(self._defaults[option])
        else:
            return super().get(
                section, option, raw=raw, vars=vars, fallback=fallback
            )

    def set(self, section, option, value=None):
        if section not in self:
            self.add_section(section)

        if (
            section == 'options' and
            self._defaults and
            option in self._defaults and
            parse_value(self._defaults[option]) == parse_value(value)
        ):
            return

        return super(ConfigParser, self).set(section, option, value)

    def set_defaults(self, defaults):
        self._defaults = defaults


class ProtectedDict(dict):
    def __init__(self, protected_values):
        self.protected_values = protected_values

        super(ProtectedDict, self).__init__(
            **protected_values
        )

    def __setitem__(self, key, value):
        if key in self.protected_values:
            return
        super(ProtectedDict, self).__setitem__(key, value)
