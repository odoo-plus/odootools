import string
import random
from .compat import Path
import configparser


def from_csv(value, custom_type=None):
    if not value:
        return []

    res = [
        val.strip() for val in value.split(',')
        if val.strip()
    ]

    if custom_type:
        res = custom_type(res)

    return res


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


class ConfigParser(configparser.ConfigParser):
    def set(self, section, option, value=None):
        if section not in self:
            self.add_section(section)
        return super(ConfigParser, self).set(section, option, value)
