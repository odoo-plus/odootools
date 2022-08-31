from ..exceptions import FileParserMissingError


class FileLoader(object):
    def __init__(self):
        self.parsers = {}

    def load_file(self, path, default_loader=None):
        loaders = self.get_loaders(path, default_loader)

        with path.open('r') as fin:
            data = fin.read()

        for loader in loaders:
            data = loader(data)

        return data

    def get_loaders(self, path, default_loader=None):
        suffixes = path.suffixes

        loaders = []

        if not suffixes and not default_loader:
            return loaders

        suffixes.reverse()

        for suffix in suffixes:
            try:
                loaders.append(self.parsers[suffix])
            except KeyError:
                raise FileParserMissingError(
                    "Cannot parse a file with the type {}".format(suffix)
                )

        return loaders
