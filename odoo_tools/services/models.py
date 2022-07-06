class BaseModel(object):
    def __init__(self, data):
        self._data = {}

        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self._data[key] = value

    @classmethod
    def parse(self, data):
        if isinstance(data, BaseModel):
            return data
        else:
            return self(data)


class ParentedObject(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent = None

    def set_parent(self, parent):
        self._parent = parent

    def get_parent(self, klass):
        current_obj = self
        while hasattr(current_obj, '_parent'):
            if isinstance(current_obj, klass):
                return current_obj
            else:
                current_obj = current_obj._parent

        if isinstance(current_obj, klass):
            return current_obj


class Extendable(object):
    def extend(self, other):
        raise NotImplementedError()
